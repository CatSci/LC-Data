import streamlit as st
import pandas as pd
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
            spectrum_line = line.strip().split('\\')[-2]  # Split and keep the part after the last backslash
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

    merged_df = pd.DataFrame(index=final_df_aggregated.index)
    # Iterate through each pair of columns and check for merging condition
    for rt1 in final_df_aggregated.columns:
        for rt2 in final_df_aggregated.columns:
            if rt1 != rt2 and abs(float(rt1) - float(rt2)) <= 0.2:
                # Check if at least one value in each row across these columns is 0
                condition = (final_df_aggregated[rt1] == 0) | (final_df_aggregated[rt2] == 0)
                if condition.all():  # If the condition is true for all rows
                    # Sum the columns and use the higher RT value as the column name
                    new_col_name = max(rt1, rt2, key=lambda x: float(x))
                    merged_df[new_col_name] = final_df_aggregated[[rt1, rt2]].sum(axis=1)
                    # Once columns are merged, they should not be considered again
                    final_df_aggregated.drop([rt1, rt2], axis=1, inplace=True)
                    break  # Break to avoid re-checking the same columns
                # Add the remaining columns that were not merged to the merged_df
    for col in final_df_aggregated.columns:
        if col not in merged_df:
            merged_df[col] = final_df_aggregated[col]
    # Sort the columns as they might be out of order after merging
    merged_df = merged_df.sort_index(axis=1)
    
    # Display the final DataFrame in the app
    st.dataframe(merged_df)

    st.download_button(
        label="Download Excel file",
        data=convert_df_to_excel(merged_df),
        file_name="processed_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
