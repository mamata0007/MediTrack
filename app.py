import streamlit as st
import pandas as pd
from datetime import date
from pathlib import Path

st.set_page_config(page_title="MediTrack", page_icon="💊", layout="wide")

st.title("💊 MediTrack")
st.subheader("Medicine Expiry & Availability Tracker")
st.write("Track medicine batches, expiry dates, and stock availability.")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DATA_FILE = DATA_DIR / "medicines.csv"

columns = [
    "Medicine Name", "Batch Number", "Quantity",
    "Expiry Date", "Minimum Stock"
]

if DATA_FILE.exists():
    df = pd.read_csv(DATA_FILE)
else:
    df = pd.DataFrame(columns=columns)

st.sidebar.header("Navigation")
page = st.sidebar.radio(
    "Choose a page",
    ["Dashboard", "Add Medicine", "Medicine Inventory"]
)

if page == "Add Medicine":
    st.header("➕ Add Medicine Batch")

    with st.form("medicine_form"):
        name = st.text_input("Medicine name")
        batch = st.text_input("Batch number")
        quantity = st.number_input("Quantity in stock", min_value=0, step=1)
        expiry = st.date_input("Expiry date", value=date.today())
        minimum = st.number_input(
            "Minimum stock alert level", min_value=0, value=10, step=1
        )
        submitted = st.form_submit_button("Save Medicine")

        if submitted:
            if not name.strip() or not batch.strip():
                st.error("Please enter both medicine name and batch number.")
            elif (
                not df.empty
                and (
                    (df["Medicine Name"].astype(str).str.lower() == name.strip().lower())
                    & (df["Batch Number"].astype(str).str.lower() == batch.strip().lower())
                ).any()
            ):
                st.error("This medicine batch already exists.")
            else:
                new_row = pd.DataFrame([{
                    "Medicine Name": name.strip(),
                    "Batch Number": batch.strip(),
                    "Quantity": int(quantity),
                    "Expiry Date": expiry.isoformat(),
                    "Minimum Stock": int(minimum)
                }])
                pd.concat([df, new_row], ignore_index=True).to_csv(
                    DATA_FILE, index=False
                )
                st.success("Medicine saved successfully!")
                st.rerun()

elif page == "Medicine Inventory":
    st.header("📦 Medicine Inventory")

    if df.empty:
        st.info("No medicines added yet. Select Add Medicine from the sidebar.")
    else:
        df["Expiry Date"] = pd.to_datetime(df["Expiry Date"], errors="coerce")
        search = st.text_input("Search by medicine name or batch number")

        filtered = df[
            df["Medicine Name"].astype(str).str.contains(
                search, case=False, na=False
            )
            | df["Batch Number"].astype(str).str.contains(
                search, case=False, na=False
            )
        ]

        st.dataframe(filtered, use_container_width=True, hide_index=True)

        st.download_button(
            "Download inventory CSV",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name="medicine_inventory.csv",
            mime="text/csv"
        )

        if not filtered.empty:
            st.divider()
            st.subheader("✏️ Update or Delete a Batch")

            selected_index = st.selectbox(
                "Select a medicine batch",
                options=filtered.index.tolist(),
                format_func=lambda i: (
                    f"{df.loc[i, 'Medicine Name']} — "
                    f"Batch {df.loc[i, 'Batch Number']}"
                )
            )

            selected = df.loc[selected_index]

            with st.form("edit_medicine_form"):
                new_name = st.text_input(
                    "Medicine name", value=str(selected["Medicine Name"])
                )
                new_batch = st.text_input(
                    "Batch number", value=str(selected["Batch Number"])
                )
                new_quantity = st.number_input(
                    "Quantity", min_value=0,
                    value=int(selected["Quantity"]), step=1
                )

                current_expiry = selected["Expiry Date"]
                if pd.isna(current_expiry):
                    current_expiry = pd.Timestamp(date.today())

                new_expiry = st.date_input(
                    "Expiry date", value=current_expiry.date()
                )
                new_minimum = st.number_input(
                    "Minimum stock", min_value=0,
                    value=int(selected["Minimum Stock"]), step=1
                )
                update_clicked = st.form_submit_button("Save Changes")

                if update_clicked:
                    if not new_name.strip() or not new_batch.strip():
                        st.error("Medicine name and batch number are required.")
                    else:
                        duplicate = (
                            (df["Medicine Name"].astype(str).str.lower()
                             == new_name.strip().lower())
                            & (df["Batch Number"].astype(str).str.lower()
                               == new_batch.strip().lower())
                            & (df.index != selected_index)
                        ).any()

                        if duplicate:
                            st.error("Another batch with this name and number exists.")
                        else:
                            df.loc[selected_index, columns] = [
                                new_name.strip(),
                                new_batch.strip(),
                                int(new_quantity),
                                new_expiry.isoformat(),
                                int(new_minimum)
                            ]
                            df.to_csv(DATA_FILE, index=False)
                            st.success("Medicine batch updated!")
                            st.rerun()

            if st.button("🗑️ Delete Selected Batch"):
                st.session_state["confirm_delete"] = True

            if st.session_state.get("confirm_delete", False):
                st.warning("Are you sure you want to delete this batch?")
                col1, col2 = st.columns(2)

                with col1:
                    if st.button("Yes, delete it"):
                        df.drop(index=selected_index).to_csv(
                            DATA_FILE, index=False
                        )
                        st.session_state["confirm_delete"] = False
                        st.success("Batch deleted.")
                        st.rerun()

                with col2:
                    if st.button("Cancel"):
                        st.session_state["confirm_delete"] = False
                        st.rerun()

        else:
            st.info("No medicines match your search.")

else:
    st.header("📊 Inventory Dashboard")

    if df.empty:
        st.info("Your inventory is empty. Add your first medicine batch.")
    else:
        df["Expiry Date"] = pd.to_datetime(
            df["Expiry Date"], errors="coerce"
        )
        today = pd.Timestamp(date.today())
        days_left = (df["Expiry Date"] - today).dt.days

        quantities = pd.to_numeric(
            df["Quantity"], errors="coerce"
        ).fillna(0)
        minimums = pd.to_numeric(
            df["Minimum Stock"], errors="coerce"
        ).fillna(0)

        expired = days_left < 0
        expiring_soon = days_left.between(0, 30)
        low_stock = quantities <= minimums

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Medicine Batches", len(df))
        c2.metric("Total Units", int(quantities.sum()))
        c3.metric("Expired Batches", int(expired.sum()))
        c4.metric("Expiring in 30 Days", int(expiring_soon.sum()))

        if expired.any():
            st.error("⚠️ Expired medicines detected. Do not dispense expired medicines.")
        if low_stock.any():
            st.warning("⚠️ Low-stock medicines detected.")
        if expiring_soon.any():
            st.warning("⚠️ Some batches expire within the next 30 days.")

        alerts = df.loc[expired | expiring_soon | low_stock].copy()

        if not alerts.empty:
            st.subheader("🚨 Items Requiring Attention")
            st.dataframe(alerts, use_container_width=True, hide_index=True)
        else:
            st.success("No expiry or low-stock alerts right now.")

        st.subheader("📈 Expiry Status Chart")
        expiry_status = pd.Series(
            "Safe for now", index=df.index, dtype="object"
        )
        expiry_status.loc[expired] = "Expired"
        expiry_status.loc[expiring_soon] = "Expiring within 30 days"

        chart_data = (
            expiry_status.value_counts()
            .rename_axis("Expiry Status")
            .reset_index(name="Number of Batches")
        )

        st.bar_chart(
            chart_data, x="Expiry Status", y="Number of Batches"
        )