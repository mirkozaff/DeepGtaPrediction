import h5py
from keras.optimizers import Adam
from load_batch import speed_steps_counter, speed_batch_generator, load_speed_dataset, SpeedDataGenerator
from utils import EarlyStopping
from keras.callbacks import TensorBoard, ModelCheckpoint
from speed_model import nvidia_model, ODFPA
import os
from keras.utils import multi_gpu_model
from ModelMGPU import ModelMGPU
import tensorflow as tf
from keras import backend as K

os.environ['TF_CPP_MIN_LOG_LEVEL']='2'
MODELS_PATH = 'speed_models/'

#Allocate memory dinamically
config = tf.ConfigProto()
config.gpu_options.allow_growth=True
sess = tf.Session(config=config)
K.set_session(sess)

print("Loading Model...")
with tf.device('/cpu:0'): #load model on CPU
	model = ODFPA(summary=True) 
gpus = 4
parallel_model = ModelMGPU(model, gpus) #load model on GPUs
print("Model Loaded. \nCompiling...")
#Setting optimizer
adam = Adam(lr=0.001, beta_1=0.9, beta_2=0.999)
#Compile model
parallel_model.compile(optimizer=adam, loss='mse', metrics=['accuracy'])
print("Compiled.")

#Setting TensorBoard
tbCallback = TensorBoard(log_dir='speed_graph/', histogram_freq=0, write_graph=False, write_images=False)

#Settig CheckpointCallback
mcpCallback = ModelCheckpoint(MODELS_PATH + 'model_checkpoint.h5', monitor='val_loss', save_weights_only=True, save_best_only=True, period=1)

#Settig EarlyStoppingtCallback
esCallback = EarlyStopping(monitor='val_loss', min_delta=0, patience=5, start_epoch = 15)

#Setting variables
batch_size = 16

#Loading dataset
train_dataset = load_speed_dataset(data_dir = 'training')
val_dataset = load_speed_dataset(data_dir = 'validation')

#Setting generators
train_generator = SpeedDataGenerator(train_dataset, batch_size)
val_generator = SpeedDataGenerator(val_dataset, batch_size)
 
#Fit model to data
print("Starting training...")
parallel_model.fit_generator(train_generator, validation_data=val_generator,
							 max_queue_size=10, workers=10, use_multiprocessing=True,
							epochs=100, verbose=1, callbacks=[tbCallback, mcpCallback, esCallback])

#Saving trained model
print('Saving trained model...')
model.save_weights(MODELS_PATH + 'trained_weights.h5')
print('Model saved. \nTraining ended.')
