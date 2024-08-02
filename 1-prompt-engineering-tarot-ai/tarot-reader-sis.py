# Import python packages
import streamlit as st
from snowflake.snowpark.context import get_active_session
import base64

# Write directly to the app
st.title("Frosty Fortunes")
st.write(
    """Feeling lost? Need some cosmic clarity?
    Well, look no further—because you've stumbled upon the perfect app!
    It's like trusting your gut... but way cooler. Dive into the mystical world of the [Rider-Waite Tarot deck](https://en.m.wikipedia.org/w/index.php?title=Rider%E2%80%93Waite_Tarot) and let the magic unfold! 🎴✨
""") 

# Get the current credentials
session = get_active_session()

image_df = session.sql("SELECT * FROM DIRECTORY(@TAROT_CARDS) WHERE RELATIVE_PATH LIKE '%.jpg'")
#st.dataframe(image_df)

def get_friendly_name(image_name):
    num2words = {1: 'Ace', 2: 'Two', 3: 'Three', 4: 'Four', 5: 'Five', 
            6: 'Six', 7: 'Seven', 8: 'Eight', 9: 'Nine', 10: 'Ten', 
            11: 'Page', 12: 'Knight', 13: 'Queen', 14: 'King'}
    friendly_name = image_name
    if image_name.startswith('RWS'):
        friendly_name = image_name.split('.')[0].split('_')[-1]
    else:
        img_name = image_name.split('.')[0]
        img_type = img_name[:-2]
        num = num2words[int(img_name[-2:])]
        if img_type == 'Pents':
            img_type = 'Pentacles'
        friendly_name = f"{num} of {img_type}"
    return friendly_name
        
# get 3 random images

image_df_sample = image_df.sample(n=3)
image_urls = image_df_sample[['RELATIVE_PATH']].collect()
img1 = image_urls[0]['RELATIVE_PATH']
img2 = image_urls[1]['RELATIVE_PATH']
img3 = image_urls[2]['RELATIVE_PATH']
#st.write(get_friendly_name(img1), get_friendly_name(img2), get_friendly_name(img3))

def get_img_str(image_name):
    mime_type = image_name.split('.')[-1:][0].lower()         
    with open(image_name, "rb") as f:
        content_bytes = f.read()
        content_b64encoded = base64.b64encode(content_bytes).decode()
        image_string = f'data:image/{mime_type};base64,{content_b64encoded}'
    return image_string
    


model = "mistral-7b"
instructions =  f"""
You are a skilled tarot reader. A querent  has asked a question has drawn three cards representing the past, present, and future. Please provide a detailed tarot reading based on the cards below, interpreting each card in the context of the given question.
Past Card: {get_friendly_name(img1)} [Describe the past card and its meaning]
Present Card: {get_friendly_name(img2)} [Describe the present card and its meaning]
Future Card: {get_friendly_name(img3)} [Describe the future card and its meaning]
Instructions:
Interpret each card individually in one phrase, explaining its significance in the context of the question.
Provide a very short cohesive narrative that links the past, present, and future interpretations together.
Conclude with a clear and short answer or advice for the querent regarding their questions to give correct answer.
"""

if prompt := st.chat_input("What does the future hold for you? Find out with Frosty Fortunes!"):
    col1, col2, col3 = st.columns(3)
    
    with col1:
       st.image(get_img_str(img1), width=200, caption = 'Past Card')
    
    with col2:
       st.image(get_img_str(img2), width=200, caption = 'Present Card')
    
    with col3:
       st.image(get_img_str(img3), width=200, caption = 'Future Card')
    
    instructions = instructions.replace("'", "\\'")
    question = prompt.replace("'", "\\'")
    llm_prompt = f"""concat(
                '{instructions}',
                '{question}')
                """
    query_ml_complete = f"""
            select snowflake.cortex.complete(
                '{model}', 
                 {llm_prompt}
                ) as response;
            """
    USER = "user"
    ASSISTANT = "ai"
    st.chat_message(USER).write(prompt)
    
    df = session.sql(query_ml_complete).to_pandas()
    st.chat_message(ASSISTANT).write(df['RESPONSE'][0]) 
