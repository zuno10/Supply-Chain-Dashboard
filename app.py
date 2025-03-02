from flask import Flask, render_template
import pandas as pd
import plotly.express as px

app = Flask(__name__)

# Load Data
orders = pd.read_csv("data/order_table.csv")
costs = pd.read_csv("data/Cost Analysis Trend.csv")
suppliers = pd.read_csv("data/suppliers.csv")
inventory_df = pd.read_csv("data/inventory.csv")
forecast_df = pd.read_csv("data/demand_forecast.csv")
transport_df = pd.read_csv("data/transportation_data.csv")
 

# Convert necessary columns to numeric
def convert_numeric(df, cols):
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.fillna(0, inplace=True)

convert_numeric(orders, ["delay_days", "fulfilled_quantity", "order_quantity"])
convert_numeric(costs, ["cost_amount"])
convert_numeric(suppliers, ["on_time_delivery_rate", "quality_rating"])
convert_numeric(inventory_df, ["stock_quantity", "reorder_level"])

# Function to format large numbers
def format_number(value):
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}K"
    else:
        return f"{value:.2f}"  # Keep cents for small values

# Calculate KPIs
total_orders = len(orders)
on_time_delivery_rate = round((orders["delay_days"] <= 0).mean() * 100, 2)
avg_fulfillment_rate = round((orders["fulfilled_quantity"] / orders["order_quantity"]).mean() * 100, 2)
avg_delay_days = round(orders["delay_days"].mean(), 2)
total_supply_chain_cost = costs["cost_amount"].sum()
supplier_performance = round((suppliers["on_time_delivery_rate"].mean() + suppliers["quality_rating"].mean()) / 2, 2)
stock_status = round((inventory_df["stock_quantity"] >= inventory_df["reorder_level"]).mean() * 100, 2)

# Generate insights based on data
def generate_insights():
    insights = []

    if avg_fulfillment_rate < 90:
        insights.append("⚠️ Fulfillment rate is below 90%. Consider optimizing supply chain efficiency.")
    else:
        insights.append("✅ Fulfillment rate is healthy. Keep maintaining efficiency.")

    if avg_delay_days > 3:
        insights.append(f"⚠️ Orders are delayed on average by {avg_delay_days} days. Investigate delivery bottlenecks.")
    else:
        insights.append("✅ Delivery delays are minimal, ensuring customer satisfaction.")

    if on_time_delivery_rate < 95:
        insights.append(f"⚠️ On-time delivery rate is only {on_time_delivery_rate}%. Consider supplier and logistics improvements.")
    else:
        insights.append("✅ On-time delivery rate is strong. Customers are receiving orders on time.")

    if total_supply_chain_cost > 1_000_000:
        insights.append(f"⚠️ Supply chain costs exceed $1M. Review high-cost areas for potential savings.")
    else:
        insights.append("✅ Supply chain costs are under control.")

    if supplier_performance < 75:
        insights.append(f"⚠️ Supplier performance score is low ({supplier_performance}). Consider renegotiating contracts or finding new suppliers.")
    else:
        insights.append("✅ Suppliers are performing well.")

    if stock_status < 50:
        insights.append(f"⚠️ Only {stock_status}% of warehouses are above reorder levels. Risk of stockouts.")
    else:
        insights.append("✅ Inventory levels are healthy.")

    return insights

# Prepare Pie Chart for Cost Breakdown
cost_breakdown = costs.groupby("category")["cost_amount"].sum().reset_index()
cost_breakdown["formatted_amount"] = cost_breakdown["cost_amount"].apply(format_number)

fig_pie = px.pie(
    cost_breakdown,
    values="cost_amount",
    names="category",
    title="💰 Supply Chain Cost Breakdown",
    hover_data={"cost_amount": True},
    labels={"cost_amount": "Total Cost ($)"},
)
fig_pie.update_traces(
    textinfo="label+percent",
    hovertemplate="<b>%{label}</b><br>Full Value: $%{value:,.2f}<extra></extra>"
)

@app.route("/")
def dashboard():
    return render_template(
        "Executive_summary.html",
        total_orders=format_number(total_orders),
        on_time_delivery_rate=on_time_delivery_rate,
        avg_fulfillment_rate=avg_fulfillment_rate,
        avg_delay_days=avg_delay_days,
        total_supply_chain_cost=format_number(total_supply_chain_cost),
        supplier_performance=supplier_performance,
        stock_status=stock_status,
        insights=generate_insights(),
        plot_pie=fig_pie.to_html(full_html=False)
    )


### orders
# Convert necessary columns
orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")
orders["actual_delivery_date"] = pd.to_datetime(orders["actual_delivery_date"], errors="coerce")
orders["promised_delivery_date"] = pd.to_datetime(orders["promised_delivery_date"], errors="coerce")

# Calculate Delay Days
orders["delay_days"] = (orders["actual_delivery_date"] - orders["promised_delivery_date"]).dt.days

# ✅ 1. Orders by Status (Pending, In-Transit, Delivered, Canceled)
order_status_counts = orders["order_status"].value_counts().reset_index()
order_status_counts.columns = ["order_status", "count"]

# ✅ 2. Delivery Performance (On-Time vs. Delayed Orders)
on_time_orders = (orders["delay_days"] <= 0).sum()
delayed_orders = (orders["delay_days"] > 0).sum()
delivery_performance = pd.DataFrame({
    "status": ["On-Time", "Delayed"],
    "count": [on_time_orders, delayed_orders]
})

# ✅ 3. Delay Distribution (Histogram)
delay_data = orders[orders["delay_days"] > 0]["delay_days"]

# ✅ 4. Order Trends Over Time (Monthly)
orders["month"] = orders["order_date"].dt.to_period("M").astype(str)
monthly_orders = orders.groupby("month").size().reset_index(name="count")

# ✅ 5. Geo Data for Deliveries (If location data exists, assuming `latitude` & `longitude` exist)
if "latitude" in orders.columns and "longitude" in orders.columns:
    geo_data = orders.dropna(subset=["latitude", "longitude", "delay_days"])
else:
    geo_data = None

# 📍 Bar Chart: Order Status Breakdown
fig_status = px.bar(
    order_status_counts,
    x="order_status",
    y="count",
    title="📦 Order Status Breakdown",
    text="count",
    labels={"order_status": "Order Status", "count": "Number of Orders"},
    color="order_status"
)

# 📍 Bar Chart: Delivery Performance (On-Time vs Delayed)
fig_delivery_perf = px.bar(
    delivery_performance,
    x="status",
    y="count",
    title="🚚 Delivery Performance",
    text="count",
    labels={"status": "Delivery Status", "count": "Number of Orders"},
    color="status"
)

# 📍 Line Chart: Monthly Order Trends
fig_trends = px.line(
    monthly_orders,
    x="month",
    y="count",
    title="📈 Monthly Order Trends",
    markers=True,
    labels={"month": "Month", "count": "Number of Orders"}
)

# 📍 Bar Chart: Delivery Delay Distribution (Fixed)
delay_counts = delay_data.value_counts().reset_index()
delay_counts.columns = ["delay_days", "count"]
delay_counts = delay_counts.sort_values("delay_days")  # Ensure correct order

fig_delays = px.bar(
    delay_counts,
    x="delay_days",
    y="count",
    title="⏳ Delivery Delay Distribution",
    text="count",
    labels={"delay_days": "Delay in Days", "count": "Number of Orders"},
    color_discrete_sequence=["#ff6f61"]
)

# Ensure x-axis shows only whole numbers
fig_delays.update_xaxes(
    type="category"  # Ensures only existing delay days appear
)



# 📍 Geo Map: Delivery Performance (if location data exists)
if geo_data is not None:
    fig_geo = px.scatter_mapbox(
        geo_data,
        lat="latitude",
        lon="longitude",
        color="delay_days",
        size_max=10,
        zoom=3,
        title="🌍 Delivery Performance by Location",
        color_continuous_scale="RdYlGn_r"
    )
    fig_geo.update_layout(mapbox_style="open-street-map")
else:
    fig_geo = None


@app.route("/orders")
def orders_dashboard():
    return render_template(
        "orders.html",
        plot_status=fig_status.to_html(full_html=False),
        plot_delivery_perf=fig_delivery_perf.to_html(full_html=False),
        plot_trends=fig_trends.to_html(full_html=False),
        plot_delays=fig_delays.to_html(full_html=False),
        plot_geo=fig_geo.to_html(full_html=False) if fig_geo else None
    )

# Suppliers
@app.route("/suppliers")
def supplier_performance_route():
    # --- Supplier Performance Table ---
    suppliers_ranked = suppliers.sort_values(by=["lead_time_days", "defect_rate"], ascending=[True, True])
    table_html = suppliers_ranked.to_html(classes="table table-striped", index=False)

    # --- Bar Chart: Lead Time Distribution ---
    fig_bar = px.bar(suppliers, x="supplier_name", y="lead_time_days", title="Supplier Lead Time Distribution")
    plot_bar = fig_bar.to_html(full_html=False)

    # --- Scatter Plot: Quality Rating vs. On-Time Delivery ---
    fig_scatter = px.scatter(suppliers, x="quality_rating", y="on_time_delivery_rate",
                             size="lead_time_days", color="defect_rate",
                             title="Quality Rating vs. On-Time Delivery",
                             hover_name="supplier_name")
    plot_scatter = fig_scatter.to_html(full_html=False)

    return render_template("suppliers.html", table_html=table_html, plot_bar=plot_bar, plot_scatter=plot_scatter)


# Convert forecast_date to datetime for proper sorting
forecast_df["forecast_date"] = pd.to_datetime(forecast_df["forecast_date"])

# workonlater
@app.route("/inventory")
def inventory_dashboard():
    """ Generates inventory insights and renders the inventory dashboard. """

    # ✅ **1. KPI Metrics**
    total_stock = inventory_df["stock_quantity"].sum()
    reorder_alerts = (inventory_df["stock_quantity"] <= inventory_df["reorder_level"]).sum()
    avg_forecast_accuracy = round(forecast_df["forecast_accuracy"].mean(), 1)

    # ✅ **2. Stock vs. Reorder Level (Bar Chart)**
    stock_fig = px.bar(
        inventory_df, x="product_id", y=["stock_quantity", "reorder_level"],
        barmode="group", title="Stock vs. Reorder Level",
        labels={"value": "Quantity", "variable": "Metric"}
    )

    # ✅ **3. Forecast Accuracy (Predicted vs. Actual Demand)**
    forecast_fig = px.line(
        forecast_df, x="forecast_date", y=["predicted_demand", "actual_demand"],
        markers=True, title="Predicted vs. Actual Demand",
        labels={"value": "Demand", "forecast_date": "Date"}
    )


    # ✅ **4. Warehouse Heatmap (Stock levels per location)**
    heatmap_fig = px.density_heatmap(
        inventory_df, x="warehouse_id", y="stock_quantity",
        title="Inventory Levels per Warehouse",
        labels={"stock_quantity": "Stock Quantity", "warehouse_id": "Warehouse"}
    )

    # ✅ **5. Top Fast-Moving & Slow-Moving Products**
    top_fast = inventory_df.nlargest(10, "avg_demand_per_day")[["product_id", "avg_demand_per_day"]]
    top_slow = inventory_df.nsmallest(10, "avg_demand_per_day")[["product_id", "avg_demand_per_day"]]

    # ✅ **6. Render the HTML Template**
    return render_template(
        "inventory.html",
        total_stock=total_stock,
        reorder_alerts=reorder_alerts,
        avg_forecast_accuracy=avg_forecast_accuracy,
        stock_chart=stock_fig.to_html(full_html=False),
        forecast_chart=forecast_fig.to_html(full_html=False),
        heatmap_chart=heatmap_fig.to_html(full_html=False),
        top_fastest=top_fast.to_html(classes="table table-striped", index=False),
        top_slowest=top_slow.to_html(classes="table table-striped", index=False)
    )
    
# Convert necessary columns to the right data types
transport_df["estimated_transit_time"] = pd.to_numeric(transport_df["estimated_transit_time"], errors="coerce")
transport_df["actual_transit_time"] = pd.to_numeric(transport_df["actual_transit_time"], errors="coerce")


@app.route("/transportation")
def transportation_dashboard():
    # 📌 **1. Key Insights Calculation**
    total_shipments = len(transport_df)
    delayed_shipments = transport_df[transport_df["shipment_status"] == "Delayed"].shape[0]
    delayed_percentage = round((delayed_shipments / total_shipments) * 100, 2)

    avg_transit_time = round(transport_df["actual_transit_time"].mean(), 1)

    carrier_performance = transport_df.groupby("carrier_name")["actual_transit_time"].mean()
    best_carrier = carrier_performance.idxmin()  # Carrier with the lowest transit time
    worst_carrier = carrier_performance.idxmax()  # Carrier with the highest transit time

    insights = [
        f"Total Shipments: {total_shipments}",
        f"Delayed Shipments: {delayed_percentage}% of total shipments",
        f"Average Transit Time: {avg_transit_time} days",
        f"Best Performing Carrier: {best_carrier} (Fastest transit time)",
        f"Worst Performing Carrier: {worst_carrier} (Slowest transit time)"
    ]

    # 📌 **2. Shipment Status Distribution (Pie Chart)**
    status_fig = px.pie(transport_df, names="shipment_status", title="🚚 Shipment Status Distribution")

    # 📌 **3. Carrier Performance (Avg Transit Time per Carrier)**
    carrier_fig = px.bar(carrier_performance.reset_index(), x="carrier_name", y="actual_transit_time",
                         title="⏳ Carrier Performance (Avg Transit Time)", labels={"actual_transit_time": "Avg Days"})

    # 📌 **4. Shipment Routes Map (Using Lat/Lon)**
    map_fig = px.scatter_mapbox(transport_df,
                                lat="origin_lat", lon="origin_lon",
                                color="shipment_status",
                                hover_name="origin_location",
                                hover_data=["destination_location", "mode_of_transport", "actual_transit_time"],
                                title="📍 Shipment Routes & Delays",
                                size_max=100,
                                zoom=3)

    map_fig.update_layout(mapbox_style="open-street-map")

    # Render `transportation.html` with the charts and insights
    return render_template("transportation.html",
                           insights=insights,
                           status_chart=status_fig.to_html(full_html=False),
                           carrier_chart=carrier_fig.to_html(full_html=False),
                           map_chart=map_fig.to_html(full_html=False))


@app.route("/costs")
def costs_dashboard():
    # 📊 **1. Supply Chain Cost Breakdown (Pie Chart)**
    cost_pie = px.pie(costs, names="category", values="cost_amount",
                       title="Supply Chain Cost Distribution",
                       hole=0.3)

    # 📊 **2. Supplier & Carrier Cost Efficiency (Bar Chart)**
    supplier_cost_efficiency = suppliers.groupby("supplier_name")["defect_rate"].mean().reset_index()
    supplier_cost_chart = px.bar(supplier_cost_efficiency, x="supplier_name", y="defect_rate",
                                 title="Supplier Cost Efficiency (Defect Rate)")

    # 📊 **3. Cost Trends Over Time (Line Chart)**
    costs["date_recorded"] = pd.to_datetime(costs["date_recorded"])
    cost_trend_chart = px.line(costs, x="date_recorded", y="cost_amount",
                               title="Cost Trends Over Time",
                               markers=True)

    return render_template("costs.html",
                           cost_pie=cost_pie.to_html(full_html=False),
                           supplier_cost_chart=supplier_cost_chart.to_html(full_html=False),
                           cost_trend_chart=cost_trend_chart.to_html(full_html=False))

if __name__ == "__main__":
    app.run(debug=True)