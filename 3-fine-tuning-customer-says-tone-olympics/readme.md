## Steps:
1. Run <code>setup.sql</code>
2. Load data into <code>amazon_reviews</code> from <code>Musical_instruments_reviews.csv</code> file. Select Only load valid data from the file.

![alt text](image.png)

3. Load data into <code>AMAZON_REVIEWS_FINETUNE</code> from <code>amazon_reviews_train_test.csv</code> file. Select Only load valid data from the file.

![alt text](image-4.png)

4. Create Notebook -> Import <code>3-fine-tuning-customer-says-tone-olympics/Amazon Products Fine Tuning with an Olympics Twist.ipynb</code> file

![alt text](image-1.png)

5. Add the <code>rouge-score</code> package

![alt text](image-2.png)


6. Run All cells, and do not forget to update the <code>CortexFineTuningWorkflow_id</code> 


![alt text](image-5.png)