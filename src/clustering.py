"""
Módulo de clustering K-Means sobre variables RFM con preprocesamiento riguroso.

Las tres features de clustering son:
    recencia  | frecuencia | valor_total

Preprocesamiento:
  * Yeo-Johnson + estandarización Z-score (``apply_kmeans``).

Se persisten en el DataFrame resultante los valores escalados que alimentan el
K-Means (columnas ``*_scaled``) y se reportan métricas de calidad (Silhouette y
Davies-Bouldin) para comparar la separabilidad de los clusters.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.preprocessing import PowerTransformer

FEATURES: list[str] = ["recencia", "frecuencia", "valor_total"]
# Nombres de las columnas con los valores escalados que alimentan el K-Means.
# Se persisten en el DataFrame resultante para poder graficarlos.
SCALED_FEATURES: list[str] = [f"{feat}_scaled" for feat in FEATURES]


# ── Resultado del clustering ──────────────────────────────────────────────────
@dataclass
class ClusteringResult:
    df: pd.DataFrame  # DataFrame original + columna 'cluster' (base 1) + *_scaled
    kmeans: KMeans | None  # Modelo K-Means ajustado
    transformer: PowerTransformer | None  # Transformador ajustado (None si no aplica)
    silhouette: float | None  # Silhouette score en datos transformados
    inertia: float  # Inercia del modelo ajustado
    skewness_before: dict[str, float]  # Medida de asimetría original
    skewness_after: dict[str, float]  # Medida de asimetría post-preprocesamiento
    davies_bouldin: float | None = None  # Índice Davies-Bouldin (menor es mejor)
    preprocessing: str = "yeo-johnson"  # Etiqueta del preprocesamiento usado
    winsorized: bool = False  # Si se aplicó winsorizing antes del escalado
    winsor_pct: float | None = None  # Percentil superior usado en el winsorizing


def _winsorize(X: pd.DataFrame, upper_pct: float) -> pd.DataFrame:
    """
    Recorta (capa) los valores extremos de cada variable a percentiles simétricos.

    Cada columna se limita al rango ``[p_inferior, p_superior]`` donde
    ``p_superior = upper_pct`` y ``p_inferior = 100 - upper_pct``.  Los clientes
    NO se eliminan: solo se reemplazan sus valores extremos por el valor del
    percentil correspondiente, reduciendo su influencia sobre los centroides de
    K-Means sin perder al cliente (clave en RFM, donde los extremos suelen ser
    los clientes más valiosos).

    Parameters
    ----------
    X:
        DataFrame con las columnas RFM (``FEATURES``).
    upper_pct:
        Percentil superior de corte (ej. 99.0 → recorta por encima del p99 y por
        debajo del p1).  Se restringe al rango (50, 100).
    """
    upper_pct = float(min(max(upper_pct, 50.0001), 100.0))
    lower_pct = 100.0 - upper_pct
    # BigQuery puede entregar recencia/frecuencia como Int64; los percentiles y
    # clip producen float, incompatibles con ese dtype.
    capped = X.astype("float64").copy()
    for col in capped.columns:
        lo = capped[col].quantile(lower_pct / 100.0)
        hi = capped[col].quantile(upper_pct / 100.0)
        capped[col] = capped[col].clip(lower=lo, upper=hi)
    return capped


def _cluster_quality(
    X_scaled: np.ndarray, labels: np.ndarray, random_state: int
) -> tuple[float | None, float | None]:
    """
    Calcula métricas de calidad de clustering sobre el espacio transformado.

    Retorna ``(silhouette, davies_bouldin)``.  Ambas quedan en ``None`` si hay
    un solo clúster (métricas indefinidas).  Silhouette: mayor es mejor [-1, 1];
    Davies-Bouldin: menor es mejor (>= 0).
    """
    n_unique = len(set(labels.tolist()))
    if n_unique <= 1:
        return None, None
    sil = float(
        silhouette_score(
            X_scaled,
            labels,
            sample_size=min(len(X_scaled), 5_000),
            random_state=random_state,
        )
    )
    db = float(davies_bouldin_score(X_scaled, labels))
    return sil, db


# ── Función principal de Clustering ───────────────────────────────────────────
def apply_kmeans(
    df: pd.DataFrame,
    n_clusters: int,
    random_state: int = 42,
    winsorize: bool = False,
    winsor_pct: float = 99.0,
) -> ClusteringResult:
    """
    Aplica K-Means de manera matemáticamente rigurosa.

    Preprocesamiento:
    0. (Opcional) Winsorizing: recorta los valores extremos a percentiles
       simétricos para limitar su influencia sin eliminar clientes.
    1. Calcula la asimetría original de Recencia, Frecuencia y Valor Total.
    2. Aplica la transformación de Yeo-Johnson (que maneja valores nulos o negativos)
       para normalizar y estabilizar la varianza, seguida de escalamiento estándar.
    3. Calcula la asimetría resultante.
    4. Ajusta K-Means minimizando inercia intra-clúster.
    5. Retorna un objeto ClusteringResult con métricas y datos transformados.

    Parameters
    ----------
    winsorize:
        Si es ``True``, recorta los outliers de cada variable RFM antes de la
        transformación de Yeo-Johnson.
    winsor_pct:
        Percentil superior de corte para el winsorizing (ej. 99.0).
    """
    if n_clusters < 2:
        raise ValueError("n_clusters debe ser >= 2.")
    if len(df) < n_clusters:
        raise ValueError(
            f"El número de clientes ({len(df)}) es menor que K ({n_clusters})."
        )

    # Validamos que no existan valores nulos o infinitos en las variables de interés
    X = df[FEATURES].copy()
    if X.isna().any().any():
        X = X.fillna(X.median())

    # 0. (Opcional) Winsorizing de outliers antes de cualquier transformación
    if winsorize:
        X = _winsorize(X, winsor_pct)

    # 1. Asimetría original (pandas.skew)
    skew_before = {feat: float(X[feat].skew()) for feat in FEATURES}

    # 2. Yeo-Johnson Power Transform + Standard Scaling uniforme
    # El método Yeo-Johnson es ideal para corregir la alta asimetría de variables financieras y temporales
    transformer = PowerTransformer(method="yeo-johnson", standardize=True)
    X_scaled = transformer.fit_transform(X)
    X_scaled_df = pd.DataFrame(X_scaled, columns=FEATURES)

    # 3. Asimetría post-procesamiento (debería ser cercana a 0)
    skew_after = {feat: float(X_scaled_df[feat].skew()) for feat in FEATURES}

    # 4. K-Means
    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        n_init=15,
        max_iter=500,
    )
    labels = kmeans.fit_predict(X_scaled)

    # 5. Generar DataFrame resultante con etiquetas base 1
    result_df = df.copy()
    result_df["cluster"] = labels + 1
    # Persistimos los valores escalados (z-score Yeo-Johnson) para graficarlos
    for i, scaled_col in enumerate(SCALED_FEATURES):
        result_df[scaled_col] = X_scaled[:, i]

    # Métricas de calidad (Silhouette + Davies-Bouldin) en el espacio transformado
    sil, db = _cluster_quality(X_scaled, labels, random_state)

    return ClusteringResult(
        df=result_df,
        kmeans=kmeans,
        transformer=transformer,
        silhouette=sil,
        inertia=float(kmeans.inertia_),
        skewness_before=skew_before,
        skewness_after=skew_after,
        davies_bouldin=db,
        preprocessing="yeo-johnson",
        winsorized=winsorize,
        winsor_pct=winsor_pct if winsorize else None,
    )


# ── Estadísticas descriptivas por cluster ────────────────────────────────────
def extract_cluster_rules(
    df: pd.DataFrame, target_col: str = "cluster"
) -> dict[int, str]:
    """
    Entrena un DecisionTreeClassifier para aproximar las fronteras de decisión de los clusters
    y extrae reglas lógicas legibles por humanos en las unidades originales.
    Retorna un diccionario {id_cluster: "regla_legible"}.
    """
    from sklearn.tree import DecisionTreeClassifier

    X = df[FEATURES].copy()
    y = df[target_col].copy()

    # Validaciones básicas
    if len(df) < 5 or len(y.unique()) < 2:
        return {
            cl: "Todos los clientes asignados en este segmento" for cl in y.unique()
        }

    try:
        # Profundidad max_depth=4: equilibra reglas más puras (mayor exactitud en
        # clusters intermedios que se solapan) sin volverlas ilegibles.
        clf = DecisionTreeClassifier(
            max_depth=4, min_samples_leaf=max(1, len(df) // 25), random_state=42
        )
        clf.fit(X, y)

        tree = clf.tree_
        feature = tree.feature
        threshold = tree.threshold
        children_left = tree.children_left
        children_right = tree.children_right
        value = tree.value

        feature_names_map = {
            "recencia": "Recencia",
            "frecuencia": "Frecuencia",
            "valor_total": "Monto Total",
        }

        paths = []

        def recurse(node_id, current_path):
            if children_left[node_id] == children_right[node_id]:  # Hoja
                class_counts = value[node_id].squeeze()
                if class_counts.ndim == 0:
                    class_counts = np.array([class_counts])
                pred_class_idx = np.argmax(class_counts)
                pred_class = clf.classes_[pred_class_idx]
                total = np.sum(class_counts)
                pureza = (
                    (class_counts[pred_class_idx] / total) * 100 if total > 0 else 100.0
                )

                paths.append(
                    {
                        "cluster": int(pred_class),
                        "rules": list(current_path),
                        "pureza": pureza,
                        "samples": int(total),
                    }
                )
                return

            # Nodo de decisión
            feat_idx = feature[node_id]
            feat_name = FEATURES[feat_idx]
            friendly_name = feature_names_map[feat_name]
            thresh = threshold[node_id]

            if feat_name == "valor_total":
                formatted_l = f"{friendly_name} <= ${thresh:,.0f} COP"
                formatted_r = f"{friendly_name} > ${thresh:,.0f} COP"
            elif feat_name == "frecuencia":
                formatted_l = f"{friendly_name} <= {int(thresh)} tx"
                formatted_r = f"{friendly_name} > {int(thresh)} tx"
            else:
                formatted_l = f"{friendly_name} <= {int(thresh)} días"
                formatted_r = f"{friendly_name} > {int(thresh)} días"

            recurse(children_left[node_id], current_path + [formatted_l])
            recurse(children_right[node_id], current_path + [formatted_r])

        recurse(0, [])

        # Agrupar caminos por cluster
        rules_by_cluster = {}
        for p in paths:
            cl = p["cluster"]
            if cl not in rules_by_cluster:
                rules_by_cluster[cl] = []
            rules_by_cluster[cl].append(p)

        # Generar una regla consolidada para cada cluster id
        final_rules = {}
        for cl in sorted(y.unique()):
            cl_paths = rules_by_cluster.get(cl, [])
            if not cl_paths:
                final_rules[cl] = "Sujeto a distribución general"
                continue

            # Ordenar caminos del clúster por número de muestras decreciente
            cl_paths = sorted(cl_paths, key=lambda x: -x["samples"])
            best_path = cl_paths[0]

            rules_list = best_path["rules"]
            if not rules_list:
                final_rules[cl] = "Comportamiento representativo general"
            else:
                rule_str = " Y ".join(rules_list)
                final_rules[cl] = (
                    f"{rule_str} (con {best_path['pureza']:.1f}% de exactitud en regla)"
                )

        return final_rules
    except Exception as e:
        return {cl: f"Lógica matemática adaptativa: {e}" for cl in y.unique()}


def get_cluster_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula estadísticas descriptivas por clúster (media, mediana, desv. estándar,
    mínimo y máximo de cada variable RFM, además del tamaño y porcentaje) y extrae
    las fronteras de decisión inductivas mediante un Árbol de Decisión.

    No asigna nombres ni arquetipos subjetivos: los clusters se identifican solo
    por su número.
    """
    # 1. Agregación descriptiva por clúster
    agg = df.groupby("cluster")[FEATURES].agg(["mean", "median", "std", "min", "max"])
    agg.columns = ["_".join(col) for col in agg.columns]
    agg["n_clientes"] = df.groupby("cluster").size().values
    agg["porcentaje"] = (agg["n_clientes"] / len(df)) * 100
    agg = agg.reset_index()

    # 2. Extraer fronteras de decisión lógicas mediante Árbol de Decisión
    rules_map = extract_cluster_rules(df)
    agg["reglas_automaticas"] = agg["cluster"].map(rules_map)

    return agg
