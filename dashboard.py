import streamlit as st
import pandas as pd
from app.core.config import settings
from supabase import create_client, Client


st.set_page_config(page_title="Finance Tracker AI Agent", page_icon="🤖", layout="wide")

@st.cache_resource
def init_connection():
    return create_client(settings.supabase_url, settings.supabase_key)

supabase: Client = init_connection()

BOT_PHONE_NUMBER = settings.admin_phone_number.replace("+", "")
WA_LINK = f"https://wa.me/{BOT_PHONE_NUMBER}?text=Hi"

# USER FACING LANDING SECTION

st.title("🤖 Autonomous Finance Tracker AI Agent")
st.markdown("### Track your expenses instantly via WhatsApp.")

st.info(
    "**Want to use the AI-Powered Finance Tracker Agent**\n\n"
    "Click the button to open WhatsApp and send 'Hi' to the Bot."
    " It will automatically guide you through the registration process!"
)

st.link_button("📱 Click Here to Connect with the AI Agent", WA_LINK, type="primary")
st.divider()

# Super Admin Dashboard
st.header("👑 Super Admin Command Center")

def fetch_data():
    users = supabase.table("users").select("*").execute()
    expenses = supabase.table("expenses").select("*, users(name)").execute()
    return users.data, expenses.data

users_data, expenses_data = fetch_data()

# processing dataframes
df_users = pd.DataFrame(users_data)
df_expenses = pd.DataFrame(expenses_data)

if not df_users.empty and not df_expenses.empty:
    # formatting dataframes
    df_expenses['created_at'] = pd.to_datetime(df_expenses['created_at'])
    df_expenses['user_name'] = df_expenses['users'].apply(lambda x : x['name'] if isinstance(x, dict) else "Unknown")

    total_users = len(df_users[df_users['is_approved'] == True])
    pending_users = len(df_users[df_users['is_approved'] == False])
    total_volume = df_expenses['amount'].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Active Users", total_users)
    col2.metric("Pending Approvals", pending_users, delta_color="inverse", delta=pending_users if pending_users > 0 else None)
    col3.metric("Total Volume Tracked", f"₹{total_volume:,.2f}")

    st.markdown("---")

    # Charts
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Spending by Category")
        category_group = df_expenses.groupby('category')['amount'].sum().reset_index()
        st.bar_chart(category_group, x='category', y='amount', color="#4CAF50")

    with chart_col2:
        st.subheader("Daily Tracking Volume")
        daily_group = df_expenses.groupby(df_expenses['created_at'].dt.date)['amount'].sum().reset_index()
        st.line_chart(daily_group, x='created_at', y='amount', color="#2196F3")

    st.markdown("---")

    # Data Tables
    table_col1, table_col2 = st.columns(2)

    with table_col1:
        st.subheader("⏳ Pending Approvals Queue")
        pending_df = df_users[df_users['is_approved'] == False]
        if not pending_df.empty:
            st.dataframe(pending_df[['name', 'phone_number', 'created_at']], hide_index=True)
            st.caption("To approve, reply 'Y' to the bot on WhatsApp, or send `#approve <phone_number>`")
        else:
            st.success("No pending approvals!")

    with table_col2:
        st.subheader("📝 Recent Global Expenses (Audit Log)")
        recent_expenses = df_expenses[['user_name', 'amount', 'category', 'description', 'created_at']].sort_values(by='created_at', ascending=False).head(50)
        st.dataframe(recent_expenses, hide_index=True)

else:
    st.warning("Not enough data to generate dashboard metrics yet. Start logging expenses on WhatsApp!")




