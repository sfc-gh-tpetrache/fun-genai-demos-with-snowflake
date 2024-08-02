## Steps:
1. Run <code>setup.sql</code>
2. Upload images to the <code>tarot_cards</code> internal stage
3. Create the SiS app: The Streamlit app comes with a default template you can delete and replace with the code from the <code>1-tarot-ai-prompt-engineering/tarot-reader-sis.py </code>
4. !!!Note: the images have to be also uploaded to the stage where the SiS app is saved, otherwise you'll get this error: <code>FileNotFoundError: [Errno 2] No such file or directory</code>

![alt text](image.png)
