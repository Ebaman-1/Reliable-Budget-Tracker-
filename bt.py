import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import io

st.set_page_config(page_title="Budget Tracker Pro", page_icon="💰", layout="wide")

# ----------------------------
# Config
# ----------------------------
REQUIRED_COLS = ["Date", "Type", "Category", "Description", "Amount"]
CATEGORY_OPTIONS = ["Food", "Transport", "Bills", "Entertainment", "Other"]
CURRENCY_OPTIONS = {"$": "USD", "₦": "NGN", "€": "EUR", "£": "GBP"}

# ----------------------------
# Ensure schema
# ----------------------------
def ensure_schema(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(columns=REQUIRED_COLS)
    for col in REQUIRED_COLS:
        if col not in df.columns:
            if col == "Date":
                df[col] = pd.Series(dtype="datetime64[ns]")
            elif col == "Amount":
                df[col] = pd.Series(dtype="float")
            else:
                df[col] = pd.Series(dtype="object")
    df = df[REQUIRED_COLS]
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    return df

# ----------------------------
# State Init
# ----------------------------
if "transactions" not in st.session_state:
    st.session_state["transactions"] = pd.DataFrame(columns=REQUIRED_COLS)

if "budgets" not in st.session_state:
    st.session_state["budgets"] = {cat: None for cat in CATEGORY_OPTIONS}

if "currency" not in st.session_state:
    st.session_state["currency"] = "$"

if "recurring" not in st.session_state:
    st.session_state["recurring"] = []  # list of dicts

if "editing" not in st.session_state:
    st.session_state["editing"] = None  # index being edited

st.session_state["transactions"] = ensure_schema(st.session_state["transactions"])

currency = st.session_state["currency"]

# ----------------------------
# Sidebar: Settings + Filters
# ----------------------------
st.sidebar.title("⚙️ Settings")

currency = st.sidebar.selectbox("Currency", list(CURRENCY_OPTIONS.keys()),
                                index=list(CURRENCY_OPTIONS.keys()).index(st.session_state["currency"]))
st.session_state["currency"] = currency

theme = st.sidebar.radio("Theme", ["Light", "Dark"], horizontal=True)
if theme == "Dark":
    st.markdown(
        """
        <style>
        body { background-color: #1e1e1e; color: #e6e6e6; }
        .stApp { background-color: #1e1e1e; }
        </style>
        """,
        unsafe_allow_html=True
    )

if st.sidebar.button("🔄 Reset Data"):
    for k in ["transactions", "budgets", "recurring", "editing"]:
        st.session_state.pop(k, None)
    st.rerun()

st.sidebar.header("🔍 Filters")
df_base = st.session_state["transactions"]

if not df_base.empty:
    search_text = st.sidebar.text_input("Search by Description", value="")
    category_choices = sorted([c for c in df_base["Category"].dropna().unique().tolist() if str(c).strip() != ""])
    filter_category = st.sidebar.multiselect("Filter by Category", options=category_choices)
    month_options = ["All"] + sorted(df_base["Date"].dropna().dt.strftime("%B %Y").unique().tolist())
    filter_month = st.sidebar.selectbox("Filter by Month", options=month_options, index=0)
else:
    search_text = ""
    filter_category = []
    filter_month = "All"

# ----------------------------
# Header
# ----------------------------
st.title("💰 Budget Tracker Pro")
st.caption("Track income & expenses, budgets, recurring items, charts, and import/export.")

# ----------------------------
# Add Transaction
# ----------------------------
st.header("➕ Add Transaction")
with st.form("transaction_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        t_type = st.radio("Type", ["Income", "Expense"], horizontal=True)
    with col2:
        t_cat = st.selectbox("Category", CATEGORY_OPTIONS)
    with col3:
        t_amt = st.number_input("Amount", min_value=0.0, format="%.2f")

    desc = st.text_input("Description")
    submit = st.form_submit_button("Add")

    if submit and t_amt > 0:
        new_row = pd.DataFrame([[datetime.now(), t_type, t_cat, desc, t_amt]], columns=REQUIRED_COLS)
        st.session_state["transactions"] = pd.concat([st.session_state["transactions"], new_row], ignore_index=True)
        st.success("✅ Transaction Added!")

# ----------------------------
# Recurring Transactions
# ----------------------------
st.header("🔁 Recurring Transactions")
with st.form("recurring_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        r_type = st.radio("Type", ["Income", "Expense"], key="rec_type", horizontal=True)
    with col2:
        r_cat = st.selectbox("Category", CATEGORY_OPTIONS, key="rec_cat")
    with col3:
        r_amt = st.number_input("Amount", min_value=0.0, format="%.2f", key="rec_amt")
    r_desc = st.text_input("Description", key="rec_desc")
    add_rec = st.form_submit_button("Add Recurring")

    if add_rec and r_amt > 0:
        st.session_state["recurring"].append({"Type": r_type, "Category": r_cat, "Amount": r_amt, "Description": r_desc})
        st.success("✅ Recurring Transaction Added!")

# ----------------------------
# Apply Filters
# ----------------------------
df = st.session_state["transactions"].copy()
if search_text:
    df = df[df["Description"].str.contains(search_text, case=False, na=False)]
if filter_category:
    df = df[df["Category"].isin(filter_category)]
if filter_month != "All":
    df = df[df["Date"].dt.strftime("%B %Y") == filter_month]

# ----------------------------
# Display Data with Edit/Delete
# ----------------------------
st.header("📊 Transaction History")
if not df.empty:
    for i, row in df.iterrows():
        with st.expander(f"{row['Date'].strftime('%Y-%m-%d')} | {row['Type']} | {row['Category']} | {currency}{row['Amount']:.2f}"):
            st.write(f"**Description:** {row['Description']}")
            if st.session_state["editing"] == i:
                with st.form(f"edit_form_{i}"):
                    new_type = st.radio("Type", ["Income", "Expense"], index=0 if row["Type"] == "Income" else 1)
                    new_cat = st.selectbox("Category", CATEGORY_OPTIONS, index=CATEGORY_OPTIONS.index(row["Category"]))
                    new_amt = st.number_input("Amount", min_value=0.0, value=float(row["Amount"]), format="%.2f")
                    new_desc = st.text_input("Description", value=row["Description"])
                    save = st.form_submit_button("Save")
                    if save:
                        st.session_state["transactions"].at[i, "Type"] = new_type
                        st.session_state["transactions"].at[i, "Category"] = new_cat
                        st.session_state["transactions"].at[i, "Amount"] = new_amt
                        st.session_state["transactions"].at[i, "Description"] = new_desc
                        st.session_state["editing"] = None
                        st.success("✅ Transaction updated!")
                        st.rerun()
            else:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"✏️ Edit {i}"):
                        st.session_state["editing"] = i
                        st.rerun()
                with col2:
                    if st.button(f"🗑️ Delete {i}"):
                        st.session_state["transactions"] = st.session_state["transactions"].drop(i).reset_index(drop=True)
                        st.success("🗑️ Transaction deleted!")
                        st.rerun()
else:
    st.info("No transactions match your filters.")

# ----------------------------
# Monthly Summary
# ----------------------------
st.subheader("📈 Monthly Summary")
current_month = datetime.now().strftime("%B %Y")
month_df = st.session_state["transactions"][st.session_state["transactions"]["Date"].dt.strftime("%B %Y") == current_month]

if not month_df.empty:
    income = month_df[month_df["Type"] == "Income"]["Amount"].sum()
    expenses = month_df[month_df["Type"] == "Expense"]["Amount"].sum()
    balance = income - expenses
    st.info(f"{current_month} – Income: {currency}{income:,.2f} | Expenses: {currency}{expenses:,.2f} | Balance: {currency}{balance:,.2f}")
else:
    st.info(f"{current_month} – Income: {currency}0.00 | Expenses: {currency}0.00 | Balance: {currency}0.00")

# ----------------------------
# Charts
# ----------------------------
st.subheader("📉 Visuals")
colA, colB = st.columns(2)

with colA:
    exp_df = st.session_state["transactions"]
    exp_df = exp_df[exp_df["Type"] == "Expense"].copy()
    if not exp_df.empty:
        pie_df = exp_df.groupby("Category", as_index=False)["Amount"].sum()
        pie = alt.Chart(pie_df).mark_arc().encode(
            theta=alt.Theta(field="Amount", type="quantitative"),
            color=alt.Color(field="Category", type="nominal"),
            tooltip=["Category", "Amount"]
        )
        st.altair_chart(pie, use_container_width=True)

with colB:
    df_sorted = st.session_state["transactions"].sort_values("Date").copy()
    if not df_sorted.empty:
        df_sorted["Delta"] = df_sorted.apply(lambda r: r["Amount"] if r["Type"] == "Income" else -r["Amount"], axis=1)
        df_sorted["Balance"] = df_sorted["Delta"].cumsum()
        line = alt.Chart(df_sorted).mark_line(point=True).encode(
            x="Date:T",
            y=alt.Y("Balance:Q", title=f"Balance ({currency})"),
            tooltip=["Date", "Balance"]
        )
        st.altair_chart(line, use_container_width=True)
