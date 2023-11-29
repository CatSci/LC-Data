import streamlit as st
from PIL import Image
import pandas as pd
from io import BytesIO

# Logo on top left
st.image('./catsci-logo.svg', width=200)  # Adjust width as needed

# Name of the script
st.title('SCR-01: LC area txt to xslx 🔁')  # Replace with your script name

# Brief description
st.markdown('''
    This scripts helps to post-process *txt* file after extracting data by [`exportPeaks.qs`](https://catsciltd-my.sharepoint.com/:u:/g/personal/pavel_elagin_catsci_com/EXPqf-lj-aJBrxlhIReZSpsBitqSQSnV2aoBFW0na1NmYQ?e=pwEcCP).
    As output you will get Excel table as below, which you can easily edit:
    |          | RT 1 | RT 2 | RT 3 | RT x |
    |----------|------|------|------|------|
    | Sample 1 | Area |      |      |      |
    | Sample 2 |      |      |      |      |
    | Sample n |      |      |      |      |
    ''')

# Spacer after table
st.markdown('''
    ''')

# Quick instruction
with st.expander("Quick instruction📝"):
    st.markdown('''
        1. Download all your *.mnova* files from Signals to one folder.
        2. Open MestReNova
            - Select *"Tools"* tab
            - *Import* -> "Multi-Open Wildcard..."
            - In the new window that opens, select folder where you saved all files and put `*.mnova` at empty box.
            - Don't forget to tick box "Open Mnova Files into a Single Document"
            - Wait ⌛
        3. You can edit integration or keep it as it is. Press folder icon "Run Script" at same *"Tools"* tab.
        4. Find and open saved script `exportPeaks.qs`
        5. Save *txt file*.
        6. Upload this *txt file* to this app as it is, enjoy your Excel table😊
    ''')

# Quick explanation
with st.expander("How it exactly works❓"):
    st.markdown('''
        In case if output data isn't consistent or maybe wrong, there is processing pipeline.
        1. File is uploaded to script and converted to DataFrame.
        2. It parses only "Sample", "RT (mins)" and "Area" columns and ignores "Peak Label".
        3. "RT (mins)" are rounded to the second decimal places (e.g. 1.23).
        4. Table is transposed and grouped by "Sample" index and "RTs" columns.
        5. All absent data is filled by zeros. It happens when peak is absent at one sample and presented at other.
        6. Hard part. To solve problem of little peak shifting. It compares the "RTs" and if difference is ≤0.02 - columns are merged.
        The final RT is highest. After merging 3.25 and 3.26, it will keep only 3.26.
        Merge works only if at least one value in each row across these columns is 0.
        So if MGears integrated big lump for two peaks. Both of them will be reported.
        7. It then drops the excess columns that are no longer needed after the merge.
        8. And finally it exports DataFrame to Excel 🔚
    ''')

# Feedback collection
st.info(
    """
    Need a feature that's not on here? Or script raised :red[error]?
    [Let us know by filling response form](https://forms.office.com/e/xJ7ibpf5jR)
    """,
    icon="⚗️",
)

# File uploader
uploaded_file = st.file_uploader("Upload your *.txt* file")

# Function to convert DataFrame to Excel file in memory
@st.cache_data
def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=True)
        writer.book.close()  # Save the workbook
    return output.getvalue()  # Get the binary content

if uploaded_file is not None:
    # Read the uploaded file
    df = pd.read_csv(uploaded_file, sep='\t', engine='python')
    # Rounding the 'RT (mins)' column to the nearest hundredth
    df['RT (mins)'] = df['RT (mins)'].round(2)

    # Pivoting the DataFrame
    # Each unique rounded 'RT (mins)' value becomes a column
    pivot_df = df.pivot_table(index='Sample Name', 
                          columns='RT (mins)', 
                          values='Area')

    #Filling NaN values with zero
    pivot_df.fillna(0, inplace=True)

    df=pivot_df
    merged_df = pd.DataFrame(index=df.index)
    columns_to_drop = set()  # Store columns that should be dropped after merging

    # Iterate through each pair of columns and check for merging condition
    for rt1 in df.columns:
        for rt2 in df.columns:
            if rt1 != rt2 and rt1 not in columns_to_drop and rt2 not in columns_to_drop:
                try:
                    # Check the difference between rt1 and rt2 is within the specified range
                    if abs(float(rt1) - float(rt2)) <= 0.02:
                        # Check if at least one value in each row across these columns is 0
                        condition = (df[rt1] == 0.0) | (df[rt2] == 0.0)
                        if condition.any():  # If the condition is true for any row
                            # Sum the columns and use the higher RT value as the column name
                            new_col_name = max(rt1, rt2, key=lambda x: float(x))
                            merged_df[new_col_name] = df[[rt1, rt2]].sum(axis=1)
                            # Mark columns for dropping
                            columns_to_drop.update([rt1, rt2])
                except ValueError:
                    # Handle cases where rt1 or rt2 cannot be converted to float
                    continue

    # Drop the processed columns from df
    df.drop(columns=list(columns_to_drop), axis=1, inplace=True)

    # Add the remaining columns that were not merged to merged_df
    for col in df.columns:
        if col not in merged_df:
            merged_df[col] = df[col]

    # Sort the columns as they might be out of order after merging
    merged_df = merged_df.sort_index(axis=1)

    # Display the final DataFrame in the app
    st.dataframe(merged_df)
    # Download intermediate table
    st.download_button(
        label="Download Area/RT table",
        data=convert_df_to_excel(merged_df),
        file_name="Area_RT.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown('''
    Now we can create SP3 table with LCAP and RRT
    ''')
    st.latex(r'''
    LCAP=\frac{A_{i}}{ \sum A }\qquad RRT= \frac{RT_{analyte}}{RT_{reference}}
    ''')
    
    start_RT, end_RT = st.select_slider(
    'Select a range of retention time, mins',
    options=merged_df.columns.to_list(),
    value=(merged_df.columns.min(), merged_df.columns.max()))
    st.write ('You selected RT starting from', start_RT, 'to', end_RT)

    option = st.selectbox(
    'Please select relative peak for RRT calculation,mins (should be within selected range)',
    (merged_df.columns.to_list()))

    st.write('You selected relative peak:', option)
    #RP check

    if not start_RT <= option <= end_RT:
        st.error(f'Relative time {option} is outside the range!')

    if st.button('Generate SP3 table'):
        # Select range of columns by min and max value and delete the rest
        selected_columns = [col for col in merged_df.columns if isinstance(col, (int, float)) and start_RT <= col <= end_RT]
        selected_data = merged_df[selected_columns]

        # Calculate the sum of each row, find the ratio, and convert to percentage
        row_sums = selected_data.iloc[:,:].sum(axis=1)
        for col in selected_columns:
            selected_data.loc[:, col] = (selected_data[col] / row_sums) * 100

        selected_data = selected_data.round(2)
        
        #Calulate RRT
        original_columns = selected_data.columns.tolist()
        new_columns = [round(col / option, 2) if isinstance(col, (int, float)) else col for col in original_columns]

        # Create a MultiIndex
        multi_index = pd.MultiIndex.from_arrays([original_columns, new_columns], names=['RT', 'RRT'])

        # Set MultiIndex for the columns
        selected_data.columns = multi_index

        # Download SP3 table
        st.download_button(
            label="Download SP3.xlsx table",
            data=convert_df_to_excel(selected_data),
            file_name="SP3 table.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Display the final DataFrame in the app
        st.dataframe(selected_data)
