import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO, BytesIO

# Streamlit app title
st.title('Spectrum Data Processor')

# File uploader
uploaded_file = st.file_uploader("Choose a file")

# Function to convert DataFrame to Excel file in memory
@st.cache
def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=True)
        writer.book.close()  # Save the workbook
    return output.getvalue()  # Get the binary content

if uploaded_file is not None:
    # Read the uploaded file
    stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
    lines = stringio.readlines()

    # Process the lines to separate tables and track Spectrum lines
    tables = {}
    current_table = []
    spectrum_line = None
    for line in lines:
        if line.startswith('Spectrum:'):
            if current_table:
                tables[spectrum_line] = current_table
                current_table = []
            spectrum_line = line.strip().split('\\')[-1]  # Split and keep the part after the last backslash
        elif line.strip():
            current_table.append(line.strip().split('\t'))

    if current_table:
        tables[spectrum_line] = current_table

    # Convert each table to a DataFrame and reshape them
    reshaped_data = []
    for spectrum, table in tables.items():
        df = pd.DataFrame(table[1:], columns=table[0])
        df = df.apply(pd.to_numeric, errors='coerce')
        df['Spectrum'] = spectrum
        reshaped_data.append(df)

    # Concatenate all tables into a single DataFrame
    final_df = pd.concat(reshaped_data)

    # Pivot the DataFrame to get 'Spectrum' as index, 'RT' as columns, and 'Area' as values
    final_df_pivot = final_df.pivot(index='Spectrum', columns='RT', values='Area')

    # Round the 'RT' values to the nearest hundredth
    rounded_rt = final_df_pivot.columns.to_series().astype(float).round(2)

    # Group by rounded 'RT' and aggregate
    final_df_aggregated = final_df_pivot.groupby(rounded_rt, axis=1).sum()

    #change index column to more short
    final_df_aggregated.index=final_df_aggregated.index.str.split('\\').str[-2]

    # Display the final DataFrame in the app
    st.dataframe(final_df_aggregated)

    st.download_button(
        label="Download Excel file",
        data=convert_df_to_excel(final_df_aggregated),
        file_name="processed_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
