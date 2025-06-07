from flask import Flask, render_template_string
import autoAlpaca

app = Flask(__name__)

INDEX_HTML = """
<h1>Admin Page</h1>
<ul>
    <li><a href='/positions'>Positions</a></li>
    <li><a href='/activities'>Activities</a></li>
</ul>
"""

@app.route('/')
def index():
    return INDEX_HTML

@app.route('/positions')
def positions():
    positions = autoAlpaca.api.list_positions()
    rows = []
    total_cost = 0.0
    total_profit = 0.0
    for p in positions:
        rows.append(f"<tr><td>{p.symbol}</td><td>{p.qty}</td><td>{p.avg_entry_price}</td>"
                    f"<td>{p.current_price}</td><td>{p.unrealized_pl}</td></tr>")
        total_cost += float(p.avg_entry_price) * int(p.qty)
        total_profit += float(p.unrealized_pl)

    table = """<table border='1'>
    <tr><th>Symbol</th><th>Qty</th><th>Avg Price</th><th>Current Price</th><th>Unrealized P/L</th></tr>
    {} 
    </table>""".format("\n".join(rows))
    summary = f"<p>Total Cost: ${total_cost:.2f} | Total Profit: ${total_profit:.2f}</p>"
    return render_template_string("""{{table|safe}}{{summary|safe}}<p><a href='/'>Back</a></p>""",
                                  table=table, summary=summary)

@app.route('/activities')
def activities():
    try:
        acts = autoAlpaca.api.get_activities()
    except Exception as e:
        return f"Error fetching activities: {e}"

    rows = []
    for a in acts:
        rows.append(
            f"<tr><td>{a.activity_type}</td><td>{getattr(a, 'symbol', '')}</td>"
            f"<td>{getattr(a, 'qty', '')}</td><td>{getattr(a, 'price', '')}</td>"
            f"<td>{getattr(a, 'side', '')}</td><td>{a.transaction_time}</td></tr>")

    table = """<table border='1'>
    <tr><th>Type</th><th>Symbol</th><th>Qty</th><th>Price</th><th>Side</th><th>Time</th></tr>
    {} 
    </table>""".format("\n".join(rows))
    return render_template_string("""{{table|safe}}<p><a href='/'>Back</a></p>""", table=table)

if __name__ == '__main__':
    app.run(port=8000, debug=True)
