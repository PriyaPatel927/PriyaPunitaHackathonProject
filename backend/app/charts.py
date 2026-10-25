"""Plotly helpers - same look as the Streamlit app. Figures are sent to the React frontend as JSON."""
import json
import plotly.graph_objects as go


def fj(fig) -> dict:
    return json.loads(fig.to_json())


def style_fig(fig, height=340):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#E5E7EB", size=13), margin=dict(l=10, r=10, t=50, b=10), height=height,
                      title_font=dict(color="#FFFFFF", size=16), legend=dict(font=dict(color="#E5E7EB")))
    fig.update_xaxes(gridcolor="#1F2A44", zerolinecolor="#1F2A44")
    fig.update_yaxes(gridcolor="#1F2A44", zerolinecolor="#1F2A44")
    return fig


def gauge(value, title, steps, rng=(0, 100), ref=None, suffix="", num_size=44):
    cfg = {"axis": {"range": list(rng), "tickcolor": "#94A3B8", "tickfont": {"color": "#CBD5E1"}},
           "bar": {"color": "#38BDF8", "thickness": 0.28}, "bgcolor": "#111827", "borderwidth": 0,
           "steps": [{"range": [a, b], "color": c} for a, b, c in steps]}
    if ref is not None:
        cfg["threshold"] = {"line": {"color": "#FFFFFF", "width": 3}, "thickness": 0.85, "value": float(ref)}
    fig = go.Figure(go.Indicator(mode="gauge+number", value=float(value),
                                 number={"suffix": suffix, "font": {"color": "#FFFFFF", "size": num_size}},
                                 title={"text": title, "font": {"color": "#E2E8F0", "size": 15}}, gauge=cfg))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#E5E7EB"), height=265, margin=dict(l=25, r=25, t=60, b=10))
    return fig
