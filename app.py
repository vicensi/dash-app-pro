
import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import base64
import io
import uuid

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
server = app.server
uploaded_dfs = {}

app.layout = html.Div([
    dbc.NavbarSimple(brand="📊 Visualizador CSV", color="primary", dark=True),
    html.Div([
        dcc.Upload(
            id='upload-data',
            children=html.Div(['Clique ou arraste arquivos CSV']),
            style={'width': '100%', 'height': '60px', 'lineHeight': '60px',
                   'borderWidth': '1px', 'borderStyle': 'dashed',
                   'borderRadius': '5px', 'textAlign': 'center', 'margin': '10px'},
            multiple=False
        ),
        html.Div(id='file-info'),
        html.Div(id='metricas'),
        dcc.Dropdown(id='x-col', placeholder="Escolha o eixo X"),
        dcc.Dropdown(id='y-col', placeholder="Escolha o eixo Y"),
        dcc.Graph(id='grafico')
    ])
])

def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    return pd.read_csv(io.StringIO(decoded.decode('utf-8')))

@app.callback(
    Output('file-info', 'children'),
    Output('metricas', 'children'),
    Output('x-col', 'options'),
    Output('y-col', 'options'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def processar_upload(contents, filename):
    if contents is None:
        return "", "", [], []

    df = parse_contents(contents, filename)
    df_id = str(uuid.uuid4())
    uploaded_dfs[df_id] = df
    app.df_id = df_id

    metricas = html.Div([
        html.H4("📌 Métricas"),
        html.P(f"Total de linhas: {df.shape[0]}"),
        html.P(f"Total de colunas: {df.shape[1]}")
    ])

    cols_num = df.select_dtypes(include='number').columns
    col_opts = [{'label': c, 'value': c} for c in cols_num]

    return html.P(f"Arquivo carregado: {filename}"), metricas, col_opts, col_opts

@app.callback(
    Output('grafico', 'figure'),
    Input('x-col', 'value'),
    Input('y-col', 'value')
)
def atualizar_grafico(x_col, y_col):
    df = uploaded_dfs.get(app.df_id)
    if df is None or x_col is None or y_col is None:
        return {}
    return px.scatter(df, x=x_col, y=y_col, title="Gráfico Interativo")

if __name__ == "__main__":
    app.run_server(debug=True)
