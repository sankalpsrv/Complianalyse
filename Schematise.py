import streamlit as st
import pandas as pd
import combinedProcess, utils
from decouple import config
import IK_templates
ik_api = config('IK_API_KEY', default = '')
openai_key = config('OPENAI_API_KEY', default = '')

st.session_state['openai_key'] = openai_key
st.session_state['ik_api'] = ik_api


@st.cache_data
def set_env(request, key):
    global ik_api, openai_key
    if request == "openai":
        openai_key = key
        st.session_state['openai_key'] = openai_key
    else:
        ik_api = key
        st.session_state['ik_api'] = ik_api
    with open('.env', 'w') as fn:
        print("Executing set_env function")
        fn.write(f"OPENAI_API_KEY={openai_key}\nIK_API_KEY={ik_api}")

@st.cache_data
def load_data(filename, start_value, end_value):

    df2 = utils.csv_parser(filename, int(start_value), int(end_value))
    return df2

@st.cache_data
def get_XML(df2, llm_selected, format_chosen):
    openai_key = st.session_state['openai_key']
    XML_responses = combinedProcess.responseGetter(openai_key, df2, llm_selected, format_chosen)
    return XML_responses

condition_for_csv = st.radio("Do you want to upload a CSV file or use your IndianKanoon API key?", ["Upload", "IndianKanoon"])

def dataframe_view(filename):

    st.write(f"First five rows of uploaded file")

    dftest = pd.read_csv(filename)

    dftest2 = dftest.head(5)

    st.table(dftest2)

if condition_for_csv == "Upload":
    st.write(
            "Upload a csv file in the same format as 'fullsections.csv' available at https://raw.githubusercontent.com/sankalpsrv/Schematise/dev/fullsections.csv and shown below")

    dataframe_view("fullsections.csv")

    uploaded_file = st.file_uploader("Choose a file")
    if uploaded_file is not None:
        filename = uploaded_file.name

else:
    if ik_api is '':
        ik_api=st.text_input("Please enter your IndianKanoon API Key")
        set_env("ikanoon", ik_api)

    else:
        print(f"IndianKanoon API key is {ik_api}")
        pass
    docnumber=st.text_input("Specify a document number to get from IndianKanoon")

    IK_templates.extract_text(docnumber, ik_api)

    filename = "sections.csv"

    dataframe_view("sections.csv")

format_chosen=st.radio(
        "Choose LegalDocML/AkomaNtoso or LegalRuleML 👉",
        key="format_chosen",
        options=["None", "legaldocml", "legalruleml"],
    )


start_value = st.text_input('Starting range', '71')
end_value = st.text_input('Ending range', '73')
df2 = load_data(filename, start_value, end_value)

view_df = st.checkbox("Show Dataframe")

if view_df:
    st.table(df2)

llm_selected = st.radio(
        "Choose OpenAI or Llama2 👉",
        key="llm_selected",
        options=["None", "OpenAI"], #Option for Llama2-7b-chat removed
    )


if llm_selected == 'OpenAI' and openai_key is '':
    openai_key_input = st.text_input("OpenAI API Key")
    set_env("openai", openai_key_input)
    
XML_responses = get_XML(df2, llm_selected, format_chosen)

st.write(XML_responses)

st.session_state['XML_resp'] = XML_responses

st.session_state['fchosen'] = format_chosen

st.session_state['llmc'] = llm_selected










