# Peace_and_Love
Group Project CS7643 Spring 2022
Team member: Tianyao Wang, Feng Wen, Yunpeng Cheng, Yuguo Zhong

Detecting hateful speech in multimodal memes can leverage AI to stop the spread of hatred and improve the experience on social media. The team investigated several start-of-the-art models, such as ViLBERT, VisualBERT, and MMBT Grid. In addition to the baseline models, the team tried different combinations of mixing original and text-removed images for a comparative study of model performance. The team also tried different data augmentation strategies and eventually applied “weak” data augmentation for multimodal pre-trained models and “strong” data augmentation for unimodal pre-trained models. Different ensemble methods were used to improve the accuracy and the ROC-AUC score. The ensembled classification model got a 0.729 accuracy and a 0.779 ROC-AUC score, both were great improvement from Facebook’s baseline model. The text generation method was used to successfully transform the hateful memes into neutral memes. 

-config - folder of yaml files of different versions of parameters we experimented 
-CSV_Log - folder of log files and predicted results of validation data and test data
-notebook - code to generate data augmented dataset, run model, ensemble model results, plot training learning curve
-deephumor - the code we used to replace text on hateful memes to make it more neutral
-Results.xlsx - the model results of different versions of parameters
