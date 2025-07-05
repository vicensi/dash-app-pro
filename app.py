import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import base64
import io
import uuid
from sklearn.linear_model import LogisticRegression

# Usuários autorizados
USERS = {"admin": "senha123"}

app = dash.Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=[dbc.themes.FLATLY])
server = app.server
logged_in_users = set()
uploaded_dfs = {}

# Layout de login
login_layout = dbc.Container([
    html.H2("🔐 Login"),
    dbc.Input(id="username", placeholder="Usuário", type="text", className="mb-2"),
    dbc.Input(id="password", placeholder="Senha", type="password", className="mb-2"),
    dbc.Button("Entrar", id="login-btn", color="primary", className="mb-2"),
    html.Div(id="login-msg", className="text-danger"),
], className="mt-5")

# Layout principal (com dashboard)
def app_layout():
    return html.Div([
        dbc.NavbarSimple(brand="📊 Dashboard Interativo", color="primary", dark=True),
        html.Div([
            dcc.Upload(
                id='upload-data',
                children=html.Div(['Clique ou arraste arquivos CSV']),
                style={'width': '100%', 'height': '60px', 'lineHeight': '60px',
                       'borderWidth': '1px', 'borderStyle': 'dashed',
                       'borderRadius': '5px', 'textAlign': 'center', 'margin': '10px'},
                multiple=True
            ),
            html.Div(id='file-info'),
            html.Div(id='metricas'),
            html.Div(id='filtros'),
            html.Button("📥 Baixar gráfico", id='download-btn'),
            dcc.Download(id='download-image'),
            html.Button("📤 Baixar dados filtrados", id='download-csv-btn'),
            dcc.Download(id='download-csv'),
            html.Br(), html.Br(),
            dcc.Tabs([
                dcc.Tab(label='📈 Gráfico Interativo', children=[
                    dcc.Dropdown(id='x-col', placeholder="Escolha o eixo X"),
                    dcc.Dropdown(id='y-col', placeholder="Escolha o eixo Y"),
                    dcc.Graph(id='grafico')
                ]),
                dcc.Tab(label='🧾 Tabela', children=[
                    dash_table.DataTable(id='tabela',
                                         style_table={'overflowX': 'auto'},
                                         page_size=10)
                ]),
                dcc.Tab(label='📃 Estatísticas', children=[
                    html.Pre(id='resumo-estat')
                ]),
                dcc.Tab(label='🧠 Simulação de Modelo', children=[
                    html.P("Simulação com modelo de regressão (placeholder)"),
                    html.Button("Executar Modelo", id='rodar-modelo'),
                    html.Div(id='output-modelo')
                ])
            ]),
            html.Button("Logout", id='logout-btn', className="mt-4"),
        ])
    ])

app.layout = html.Div("TESTE OK")

# Este callback mostra a tela de login ao abrir
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname'),
)
def route_page(pathname):
    return login_layout 

# Este callback executa o login e carrega o dashboard se a senha estiver certa
@app.callback(
    Output('page-content', 'children'),
    Output('login-msg', 'children'),
    Input('login-btn', 'n_clicks'),
    State('username', 'value'),
    State('password', 'value'),
    prevent_initial_call=True
)
def validar_login(n, user, senha):
    if user in USERS and USERS[user] == senha:
        logged_in_users.add(user)
        return app_layout(), ""
    return login_layout, "Usuário ou senha inválido."

# Este callback faz logout
@app.callback(
    Output('page-content', 'children'),
    Input('logout-btn', 'n_clicks'),
    prevent_initial_call=True
)
def logout(n):
    logged_in_users.clear()
    return login_layout
    
# ======= Funções do dashboard a partir daqui =======

def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    return pd.read_csv(io.StringIO(decoded.decode('utf-8')))

@app.callback(
    Output('file-info', 'children'),
    Output('metricas', 'children'),
    Output('x-col', 'options'),
    Output('y-col', 'options'),
    Output('tabela', 'data'),
    Output('tabela', 'columns'),
    Output('resumo-estat', 'children'),
    Output('filtros', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def processar_upload(list_contents, list_names):
    if list_contents is None:
        return "", "", [], [], [], [], "", ""

    all_data = []
    for contents, name in zip(list_contents, list_names):
        df = parse_contents(contents, name)
        all_data.append(df)

    df_all = pd.concat(all_data)
    df_all.reset_index(drop=True, inplace=True)
    data_id = str(uuid.uuid4())
    uploaded_dfs[data_id] = df_all
    app.df_id = data_id

    metricas = html.Div([
        html.H4("📌 Métricas"),
        html.P(f"Total de linhas: {df_all.shape[0]}"),
        html.P(f"Total de colunas: {df_all.shape[1]}")
    ])

    cols_num = df_all.select_dtypes(include='number').columns
    col_opts = [{'label': c, 'value': c} for c in cols_num]

    filtros = []
    cols_cat = df_all.select_dtypes(include='object').columns
    if len(cols_cat) > 0:
        col_cat = cols_cat[0]
        filtros.append(html.Label(f"Filtrar por {col_cat}"))
        filtros.append(dcc.Dropdown(id='filtro-cat',
                                    options=[{'label': v, 'value': v} for v in df_all[col_cat].unique()],
                                    multi=True))
    else:
        filtros.append(html.P("Nenhuma coluna categórica disponível."))

    return (
        html.P(f"{len(all_data)} arquivo(s) carregado(s)."),
        metricas,
        col_opts,
        col_opts,
        df_all.head(20).to_dict('records'),
        [{'name': i, 'id': i} for i in df_all.columns],
        df_all.describe().to_string(),
        filtros
    )

@app.callback(
    Output('grafico', 'figure'),
    Input('x-col', 'value'),
    Input('y-col', 'value'),
    Input('filtro-cat', 'value')
)
def atualizar_grafico(x_col, y_col, filtro_val):
    df = uploaded_dfs.get(app.df_id)
    if df is None or x_col is None or y_col is None:
        return {}

    col_cat = df.select_dtypes(include='object').columns
    if filtro_val and len(col_cat) > 0:
        df = df[df[col_cat[0]].isin(filtro_val)]

    return px.scatter(df, x=x_col, y=y_col, color=col_cat[0] if len(col_cat) > 0 else None)

@app.callback(
    Output("download-csv", "data"),
    Input("download-csv-btn", "n_clicks"),
    Input('filtro-cat', 'value'),
    prevent_initial_call=True
)
def baixar_csv(n, filtro_val):
    df = uploaded_dfs.get(app.df_id)
    col_cat = df.select_dtypes(include='object').columns
    if filtro_val and len(col_cat) > 0:
        df = df[df[col_cat[0]].isin(filtro_val)]
    return dcc.send_data_frame(df.to_csv, "dados_filtrados.csv")

@app.callback(
    Output("output-modelo", "children"),
    Input("rodar-modelo", "n_clicks"),
    prevent_initial_call=True
)
def simular_modelo(n):
    df = uploaded_dfs.get(app.df_id)
    df_num = df.select_dtypes(include='number').dropna()
    if df_num.shape[1] < 2:
        return "Dados insuficientes."
    X = df_num.iloc[:, :-1]
    y = (df_num.iloc[:, -1] > df_num.iloc[:, -1].mean()).astype(int)
    model = LogisticRegression()
    model.fit(X, y)
    return f"Acurácia simulada: {model.score(X, y):.2%}"
