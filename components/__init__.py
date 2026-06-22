"""
Paquete de componentes UI reutilizables para la aplicación RFM.

Cada módulo expone una o más funciones de renderizado con responsabilidad única,
siguiendo una arquitectura similar a componentes React pero adaptada a Streamlit.

Componentes disponibles
-----------------------
styles          render_styles()            → Inyecta CSS global
header          render_header()            → Hero + banner de modo dev
sidebar         render_sidebar()           → Panel lateral; retorna SidebarConfig
data_source     render_data_source()       → Selector de fuente; retorna DataSourceConfig
metrics_bar     render_metrics_bar()       → Fila de KPIs resumen
tab_visualizations  render_viz_tab()       → Tab de gráficos
tab_statistics  render_stats_tab()         → Tab de estadísticas por cluster
tab_data        render_data_tab()          → Tab de tabla de datos
empty_state     render_empty_state()       → Placeholder sin datos
"""
