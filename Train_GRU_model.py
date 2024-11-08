# -*- coding: utf-8 -*-
"""Train_Parameter_Model.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1NzbH5VnvpFnyGCCB5XFmxRCwvDrr-wuA
"""

#################################################  User Inputs  #######################################################################
EPOCH = 150
train_fraction = 0.8
timesteps, input_dim = 50, 8
output_list = [ 0 , 1 , 2 ]
out_key = [ 'Stress strain curve' , 'Plastic dissipation' , 'Elastic strain energy' ]
n_output_channels = len(output_list)

#################################################  User Inputs  #######################################################################



import tensorflow as tf
from tensorflow.keras.layers import Dense, TimeDistributed, GRU , concatenate, BatchNormalization , Conv2D , MaxPooling2D , Flatten , Reshape , RepeatVector, LeakyReLU
from tensorflow.keras import Input, Model
import numpy as np
import glob
import re
import matplotlib.pyplot as plt
# from keras.utils import multi_gpu_model
from sklearn.utils import shuffle
import os
from tensorflow.keras import regularizers
from tensorflow.keras import optimizers
from sklearn.preprocessing import StandardScaler , MinMaxScaler , RobustScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from tensorflow.keras import layers, losses
from tensorflow.keras.models import Model
from keras.utils.vis_utils import plot_model
import pickle
import time
import keras.backend as K

try:
    os.mkdir('/content/Results')
except:
    pass

from google.colab import drive
drive.mount('/content/drive/', force_remount=True)

All_train_time = []
for REP in range( 1 ):
    # REP = 100
    print('Repetition ' , REP+1 , '.....')
    # Create output dir
    try:
        os.mkdir('/content/Results/Repetition'+str(REP))
    except:
        pass

    #################################################  Read Inputs  #######################################################################
    f = open( '/content/drive/MyDrive/Colab Notebooks/Poly_ML/Parameter_model/Parameter_Input_arr_x100.npy' , 'rb' )
    x_arry = np.load( f )
    f.close()

    f = open( '/content/drive/MyDrive/Colab Notebooks/Poly_ML/Parameter_model/Parameter_Output_50_steps_x100.npy' , 'rb' )
    y = np.load( f )
    f.close()


    # Filter outputs
    y = y[:,:,output_list]
    print('Model outputs are: ')
    for i in output_list:
        print( out_key[ i ] )


    print('\nTotal data dimensions:')
    print( x_arry.shape , y.shape  )
    num_examples = x_arry.shape[0]

    # Shuffle data
    x_arry , y = shuffle(x_arry , y)

    # Split data
    train_range    = int(num_examples * train_fraction)
    x_train_arry        = x_arry[:train_range,:,:]
    y_train        = y[:train_range,:,:]
    print('Training data dimensions:')
    print(x_train_arry.shape , y_train.shape)

    x_test_arry           = x_arry[train_range:,:,:]
    y_test_gt        = y[train_range:,:,:]
    print('Testing data dimensions:')
    print(y_test_gt.shape)


    #################################################  Scale Inputs  #######################################################################
    # Scale datasets
    xScalers = []
    for ss in range(8):
        curr_scaler = StandardScaler()
        curr_scaler.fit( x_train_arry[:,:,ss] )
        xScalers.append( curr_scaler )

        # Transform array inputs
        x_train_arry[:,:,ss] = curr_scaler.transform( x_train_arry[:,:,ss] )
        x_test_arry[:,:,ss] = curr_scaler.transform( x_test_arry[:,:,ss] )


    # Transform y data
    yScalers = []
    for ss in range(n_output_channels):
        curr_scaler = StandardScaler()
        curr_scaler.fit( y_train[:,:,ss] )
        yScalers.append( curr_scaler )

        # Transform
        y_train[:,:,ss] = curr_scaler.transform( y_train[:,:,ss] )
        y_test_gt[:,:,ss] = curr_scaler.transform( y_test_gt[:,:,ss] )

    # Finally, store all scalers
    f = open('/content/Results/Repetition'+str(REP)+'/Scalers.npy','wb')
    np.save( f , np.array([ xScalers , yScalers ],dtype=object) )
    f.close()
    print('Done scaling all data!')


    xtrain2_full = x_train_arry.copy()
    y_full = y_train.copy()
    s = xtrain2_full.shape
    print('Total training size ' , s[0] )
    pct_count = 5
    #for pct in [ 0.05 , 0.1 , 0.4 , 0.6 , 0.8 , 0.9 ,  1.]:
    for pct in [ 1. ]:
        pct_count += 1
        print('\n\nUsing ' , pct*100 , '% of total training data in training!')
        SIZE = int(round(pct*s[0]))
        print(SIZE)
        x_train_arry = xtrain2_full[ : SIZE ]
        y_train = y_full[ : SIZE ]




        #################################################  Build and train model  #######################################################################
        # Array input
        i = Input(shape=( timesteps, input_dim ))

        # GRU layers
        o = GRU(475, return_sequences=True , activation='tanh' )(i)
        o = GRU(475, return_sequences=True , activation='tanh' )(o)
        o = GRU(475, return_sequences=True , activation='tanh' )(o)
        o = TimeDistributed( Dense(n_output_channels) )(o)
        m = Model(inputs=[i], outputs=[o])

        # Choose optimizer
        lr_schedule = tf.keras.optimizers.schedules.InverseTimeDecay(
          1e-3,
          decay_steps= 2000,
          decay_rate=1.,
          staircase=True)
        opt = optimizers.Adam( lr_schedule )

        # Put model together
        m.compile(optimizer= opt , loss=tf.keras.losses.MeanAbsoluteError(), metrics=[tf.keras.metrics.MeanSquaredError()])
        # m.summary()
        # plot_model(m  , to_file='model_plot.png' , show_shapes=True, show_layer_names=True)


        # Call-backs
        early = tf.keras.callbacks.EarlyStopping(monitor = 'loss', min_delta = 1e-6, patience = 10, verbose = 1)
        st = time.time()
        m_his = m.fit( x_train_arry.copy() , y_train.copy(), epochs=EPOCH, validation_split=0.15, shuffle=True ,callbacks = [early], verbose = 1 , batch_size = 500 )
        train_time = time.time() - st

        All_train_time.append( train_time )

        kk = list(m_his.history.keys())
        np_loss_history = np.array( m_his.history[ kk[0] ] )
        np.savetxt('/content/Results/Repetition'+str(REP)+"/PCT-"+str(pct_count) +"loss.txt", np_loss_history, delimiter=",")

        np_v_loss_history = np.array( m_his.history[ kk[2] ] )
        np.savetxt('/content/Results/Repetition'+str(REP)+"/PCT-"+str(pct_count) +"val_loss.txt", np_v_loss_history, delimiter=",")

        np_metric_history = np.array( m_his.history[ kk[1] ] )
        np.savetxt('/content/Results/Repetition'+str(REP)+"/PCT-"+str(pct_count) +"metric.txt", np_metric_history, delimiter=",")

        np_val_metric_history = np.array( m_his.history[ kk[3] ] )
        np.savetxt('/content/Results/Repetition'+str(REP)+"/PCT-"+str(pct_count) +"val_metric.txt", np_val_metric_history, delimiter=",")


        # save model and architecture to single file
        try:
            m.save('/content/Results/Repetition'+str(REP)+"/PCT-"+str(pct_count) +"GRU_model.h5")
            print("Saved model to disk")
        except:
            pass

        print('Predicting')
        y_test_pred = m.predict(  x_test_arry )
        print('Done Predicting')
        model_evaluation = m.evaluate(x= x_test_arry , y=y_test_gt, batch_size= 100 )
        print(model_evaluation)



        #################################################  Save predictions  #######################################################################
        # Apply inverse transform to outputs
        y_test_gt_ori_scale = np.zeros_like( y_test_gt )
        for ss , curr_scaler in zip( range(n_output_channels) , yScalers ):
            y_test_gt_ori_scale[:,:,ss] = curr_scaler.inverse_transform( y_test_gt[:,:,ss] )
            y_test_pred[:,:,ss] = curr_scaler.inverse_transform( y_test_pred[:,:,ss] )

        # Save data
        f = open( '/content/Results/Repetition'+str(REP)+"/PCT-"+str(pct_count) +'Y_data.npy' , 'wb' )
        np.save( f , np.array([ y_test_gt_ori_scale ] ,dtype=object) )
        f.close()
        f = open( '/content/Results/Repetition'+str(REP)+"/PCT-"+str(pct_count) +'Predictions.npy' , 'wb' )
        np.save( f , np.array([ y_test_pred ] ,dtype=object) )
        f.close()



# Save all train times
f = open( '/content/Results/TrainTime.npy' , 'wb' )
np.save( f , All_train_time )
f.close()
print('\n\nTraining time:')
print( All_train_time )
