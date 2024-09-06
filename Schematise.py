import streamlit as st
import pandas as pd
import combinedProcess, utils
from decouple import config
import IK_templates





def set_env(key = '', request = ''):
    global ik_api, openai_key
    if request == "openai":
        openai_key = key
        st.session_state['openai_key'] = openai_key
    elif request == "ikanoon":
        ik_api = key
        st.session_state['ik_api'] = ik_api
    else:
        
        return st.session_state['ik_api'], st.session_state['openai_key']

@st.cache_data
def load_data(filename, start_value, end_value):

    df2 = utils.csv_parser(filename, int(start_value), int(end_value))
    return df2

@st.cache_data
def get_XML(df2, llm_selected, format_chosen):
    openai_key = st.session_state['openai_key']
    XML_responses = combinedProcess.responseGetter(openai_key, df2, llm_selected, format_chosen)
    return XML_responses

def dataframe_view(filename):

    st.write(f"First five rows of uploaded file")

    dftest = pd.read_csv(filename)

    dftest2 = dftest.head(5)

    st.table(dftest2)

def main():
    
    filename = "fullsections.csv"

    if 'openai_key' not in st.session_state:
        st.session_state['openai_key'] = ''

    if 'ik_api' not in st.session_state:
        st.session_state['ik_api'] = ''

    
    ik_api, openai_key = set_env()

    st.session_state['openai_key'] = openai_key
    st.session_state['ik_api'] = ik_api
    
    st.image("ikanoon6_powered_transparent.png")
    

    st.image('Schematise-logo-light.png')

    condition_for_csv = st.radio("Do you want to upload a CSV file or use your IndianKanoon API key?", ["Upload", "IndianKanoon"])



    if condition_for_csv == "Upload":
        st.write(
                "Upload a csv file in the same format as 'fullsections.csv' available at https://raw.githubusercontent.com/sankalpsrv/Schematise/dev/fullsections.csv and shown below")

        dataframe_view("fullsections.csv")

        uploaded_file = st.file_uploader("Choose a file")

        if uploaded_file is not None:
            filename = uploaded_file.name

    else:
        if ik_api == '':
            ik_api=st.text_input("Please enter your IndianKanoon API Key")
            set_env(ik_api, "ikanoon")

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


    if llm_selected == 'OpenAI' and openai_key == '':
        print ("Session state variable for OpenAI is", st.session_state['openai_key'])
        openai_key_input = st.text_input("OpenAI API Key")
        set_env(openai_key_input, "openai")

    try:
        XML_responses = get_XML(df2, llm_selected, format_chosen)
        st.download_button(label = "Download XML generated", 
                            data = str(XML_responses),
                            file_name = f'{format_chosen}_{start_value}_{end_value}.txt')

    except ValueError:
        st.write("Error: Please enter a valid OpenAI key")

    except UnboundLocalError:
        st.write("Error: Please follow all earlier steps for selecting format, number of sections, and llm")


    try:
        st.write(XML_responses)

    except NameError:
        st.write("Error: Please complete the earlier steps for computing XML_responses")

    try:
        st.session_state['XML_resp'] = XML_responses

    except NameError:
        st.write("Error: Please complete the earlier steps for storing XML_responses")

    try:
        st.session_state['fchosen'] = format_chosen

    except NameError:
        st.write("Error: Please complete the earlier steps for selecting format: LegalDocML or LegalRuleML")

    try:
        st.session_state['llmc'] = llm_selected

    except NameError:
        st.write("Error: Please complete the earlier steps for selecting LLM")


if __name__ == "__main__":

    buttonpress = False

    if 'disclaimer' not in st.session_state:
        st.session_state['disclaimer'] = False
    
    if st.session_state['disclaimer'] is False:
        
        st.error("Disclaimer: This is an AI application that will generate XML output for a law inputted by you. It is not a replacement for legal advice.")

        buttonpress= st.button("Yes, I understand. Please take me to the application")

    if buttonpress is True or st.session_state['disclaimer'] is True:
        st.error("You have accepted the disclaimer.")
        st.session_state['disclaimer'] = True
        main()
        

        
   







