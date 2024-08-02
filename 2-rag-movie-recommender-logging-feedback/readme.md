## Steps:
1. Run <code>setup.sql</code>
2. Load data into <code>MOVIES_METADATA</code> from <code>movies_metadata.csv</code> file. Select Only load valid data from the file.

![alt text](image.png)
![alt text](image-1.png)
![alt text](image-2.png)

3. Create Notebook -> Import <code>2-rag-movie-recommender-logging-feedback/Movies Recommender.ipynb</code> file

![alt text](image-3.png)

4. Add the <code>snowflake.core</code> package
![alt text](image-4.png)

5. Run All cells

![alt text](image-5.png)

6. Create the SiS app: The Streamlit app comes with a default template you can delete and replace with the code from the <code>2-rag-movie-recommender-logging-feedback/movie-recommender-sis.py </code>
