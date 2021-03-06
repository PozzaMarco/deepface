import os
from tqdm import tqdm
import numpy as np
import pandas as pd
import cv2
import time
import re

import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from ..basemodels import VGGFace, OpenFace, Facenet, FbDeepFace, DeepID
from ..extendedmodels import Age, Gender, Race, Emotion
from . import functions, realtime, distance as dst

def analysis(db_path, model_name, distance_metric, enable_face_analysis = False):
	
	input_shape = (224, 224)
	input_shape_x = input_shape[0]; input_shape_y = input_shape[1]
	
	text_color = (255,255,255)
	
	employees = []
	#check passed db folder exists
	if os.path.isdir(db_path) == True:
		for r, d, f in os.walk(db_path): # r=root, d=directories, f = files
			for file in f:
				if ('.jpg' in file):
					#exact_path = os.path.join(r, file)
					exact_path = r + "/" + file
					#print(exact_path)
					employees.append(exact_path)
					
	if len(employees) == 0:
		print("WARNING: There is no image in this path ( ", db_path,") . Face recognition will not be performed.")
	
	#------------------------
	
	if len(employees) > 0:
		if model_name == 'VGG-Face':
			print("Using VGG-Face model backend and", distance_metric,"distance.")
			model = VGGFace.loadModel()
			input_shape = (224, 224)	
		
		elif model_name == 'OpenFace':
			print("Using OpenFace model backend", distance_metric,"distance.")
			model = OpenFace.loadModel()
			input_shape = (96, 96)
		
		elif model_name == 'Facenet':
			print("Using Facenet model backend", distance_metric,"distance.")
			model = Facenet.loadModel()
			input_shape = (160, 160)
		
		elif model_name == 'DeepFace':
			print("Using FB DeepFace model backend", distance_metric,"distance.")
			model = FbDeepFace.loadModel()
			input_shape = (152, 152)
		
		elif model_name == 'DeepID':
			print("Using DeepID model backend", distance_metric,"distance.")
			model = DeepID.loadModel()
			input_shape = (55, 47)
		
		elif model_name == 'Dlib':
			print("Using Dlib model backend", distance_metric,"distance.")
			from deepface.basemodels.DlibResNet import DlibResNet
			model = DlibResNet()
			input_shape = (150, 150)
		
		else:
			raise ValueError("Invalid model_name passed - ", model_name)
		#------------------------
		
		input_shape_x = input_shape[0]
		input_shape_y = input_shape[1]
		
		#tuned thresholds for model and metric pair
		threshold = functions.findThreshold(model_name, distance_metric)
		
	#------------------------
	#facial attribute analysis models
		
	if enable_face_analysis == True:
		
		tic = time.time()
		
		emotion_model = Emotion.loadModel()
		print("Emotion model loaded")
		
		age_model = Age.loadModel()
		print("Age model loaded")
		
		gender_model = Gender.loadModel()
		print("Gender model loaded")
		
		toc = time.time()
		
		print("Facial attribute analysis models loaded in ",toc-tic," seconds")
	
	#------------------------
	
	#find features for employee list
	
	tic = time.time()
	
	pbar = tqdm(range(0, len(employees)), desc='Finding features')
	
	features = []
	#for employee in employees:
	for index in pbar:
		employee = employees[index]
		pbar.set_description("Finding feature for %s" % (employee.split("/")[-1]))
		feature = []
		img = functions.preprocess_face(img = employee, target_size = (input_shape_y, input_shape_x), enforce_detection = False)
		img_representation = model.predict(img)[0,:]
		
		feature.append(employee)
		feature.append(img_representation)
		features.append(feature)
	
	df = pd.DataFrame(features, columns = ['employee', 'feature'])
	df['distance_metric'] = distance_metric
	
	toc = time.time()
	
	print("features found for given data set in ", toc-tic," seconds")
	
	#-----------------------

	time_threshold = 5; frame_threshold = 5
	pivot_img_size = 112 #face recognition result image

	#-----------------------
	
	opencv_path = functions.get_opencv_path()
	face_detector_path = opencv_path+"haarcascade_frontalface_default.xml"
	face_cascade = cv2.CascadeClassifier(face_detector_path)
	
	#-----------------------

	freeze = False
	face_detected = False
	face_included_frames = 0 #freeze screen if face detected sequentially 5 frames
	freezed_frame = 0
	tic = time.time()

	cap = cv2.VideoCapture(0) #webcam
	#cap = cv2.VideoCapture("C:/Users/IS96273/Desktop/skype-video-1.mp4") #video

	while(True):
		ret, img = cap.read()
		
		#cv2.namedWindow('img', cv2.WINDOW_FREERATIO)
		#cv2.setWindowProperty('img', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
		
		raw_img = img.copy()
		resolution = img.shape
		
		resolution_x = img.shape[1]; resolution_y = img.shape[0]

		if freeze == False: 
			faces = face_cascade.detectMultiScale(img, 1.3, 5)
			
			if len(faces) == 0:
				face_included_frames = 0
		else: 
			faces = []
		
		detected_faces = []
		face_index = 0
		for (x,y,w,h) in faces:
			if w > 130: #discard small detected faces
				
				face_detected = True
				if face_index == 0:
					face_included_frames = face_included_frames + 1 #increase frame for a single face
				
				cv2.rectangle(img, (x,y), (x+w,y+h), (67,67,67), 1) #draw rectangle to main image
				
				cv2.putText(img, str(frame_threshold - face_included_frames), (int(x+w/4),int(y+h/1.5)), cv2.FONT_HERSHEY_SIMPLEX, 4, (255, 255, 255), 2)
				
				detected_face = img[int(y):int(y+h), int(x):int(x+w)] #crop detected face
				
				#-------------------------------------
				
				detected_faces.append((x,y,w,h))
				face_index = face_index + 1
				
				#-------------------------------------
				
		if face_detected == True and face_included_frames == frame_threshold and freeze == False:
			freeze = True
			#base_img = img.copy()
			base_img = raw_img.copy()
			detected_faces_final = detected_faces.copy()
			tic = time.time()
		
		if freeze == True:

			toc = time.time()
			if (toc - tic) < time_threshold:
				
				if freezed_frame == 0:
					img = base_img.copy()
					#img = np.zeros(resolution, np.uint8) #here, np.uint8 handles showing white area issue
					
					for detected_face in detected_faces_final:
						x = detected_face[0]; y = detected_face[1]
						w = detected_face[2]; h = detected_face[3]
												
						cv2.rectangle(img, (x,y), (x+w,y+h), (67,67,67), 1) #draw rectangle to main image
						
						#-------------------------------
						
						#apply deep learning for custom_face
						
						custom_face = base_img[y:y+h, x:x+w]
						
						#-------------------------------
						#facial attribute analysis
						
						if enable_face_analysis == True:
							
							gray_img = functions.preprocess_face(img = custom_face, target_size = (48, 48), grayscale = True, enforce_detection = False)
							emotion_labels = ['Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral']
							emotion_predictions = emotion_model.predict(gray_img)[0,:]
							sum_of_predictions = emotion_predictions.sum()
							
							mood_items = []
							for i in range(0, len(emotion_labels)):
								mood_item = []
								emotion_label = emotion_labels[i]
								emotion_prediction = 100 * emotion_predictions[i] / sum_of_predictions
								mood_item.append(emotion_label)
								mood_item.append(emotion_prediction)
								mood_items.append(mood_item)
							
							emotion_df = pd.DataFrame(mood_items, columns = ["emotion", "score"])
							emotion_df = emotion_df.sort_values(by = ["score"], ascending=False).reset_index(drop=True)
							
							#background of mood box
							
							#transparency
							overlay = img.copy()
							opacity = 0.4
							
							if x+w+pivot_img_size < resolution_x:
								#right
								cv2.rectangle(img
									#, (x+w,y+20)
									, (x+w,y)
									, (x+w+pivot_img_size, y+h)
									, (64,64,64),cv2.FILLED)
									
								cv2.addWeighted(overlay, opacity, img, 1 - opacity, 0, img)
								
							elif x-pivot_img_size > 0:
								#left
								cv2.rectangle(img
									#, (x-pivot_img_size,y+20)
									, (x-pivot_img_size,y)
									, (x, y+h)
									, (64,64,64),cv2.FILLED)
								
								cv2.addWeighted(overlay, opacity, img, 1 - opacity, 0, img)
							
							for index, instance in emotion_df.iterrows():
								emotion_label = "%s " % (instance['emotion'])
								emotion_score = instance['score']/100
								
								bar_x = 35 #this is the size if an emotion is 100%
								bar_x = int(bar_x * emotion_score)

								if x+w+pivot_img_size < resolution_x:
									
									text_location_y = y + 20 + (index+1) * 20
									text_location_x = x+w
									
									if text_location_y < y + h:
										cv2.putText(img, emotion_label, (text_location_x, text_location_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
										
										cv2.rectangle(img
											, (x+w+70, y + 13 + (index+1) * 20)
											, (x+w+70+bar_x, y + 13 + (index+1) * 20 + 5)
											, (255,255,255), cv2.FILLED)
								
								elif x-pivot_img_size > 0:
									
									text_location_y = y + 20 + (index+1) * 20
									text_location_x = x-pivot_img_size
									
									if text_location_y <= y+h:
										cv2.putText(img, emotion_label, (text_location_x, text_location_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
										
										cv2.rectangle(img
											, (x-pivot_img_size+70, y + 13 + (index+1) * 20)
											, (x-pivot_img_size+70+bar_x, y + 13 + (index+1) * 20 + 5)
											, (255,255,255), cv2.FILLED)
							
							#-------------------------------
							
							face_224 = functions.preprocess_face(img = custom_face, target_size = (224, 224), grayscale = False, enforce_detection = False)
							
							age_predictions = age_model.predict(face_224)[0,:]
							apparent_age = Age.findApparentAge(age_predictions)
						
							#-------------------------------
							
							gender_prediction = gender_model.predict(face_224)[0,:]
							
							if np.argmax(gender_prediction) == 0:
								gender = "W"
							elif np.argmax(gender_prediction) == 1:
								gender = "M"
							
							#print(str(int(apparent_age))," years old ", dominant_emotion, " ", gender)
							
							analysis_report = str(int(apparent_age))+" "+gender
							
							#-------------------------------
							
							info_box_color = (46,200,255)
							
							#top
							if y - pivot_img_size + int(pivot_img_size/5) > 0:
								
								triangle_coordinates = np.array( [
									(x+int(w/2), y)
									, (x+int(w/2)-int(w/10), y-int(pivot_img_size/3))
									, (x+int(w/2)+int(w/10), y-int(pivot_img_size/3))
								] )
								
								cv2.drawContours(img, [triangle_coordinates], 0, info_box_color, -1)
								
								cv2.rectangle(img, (x+int(w/5), y-pivot_img_size+int(pivot_img_size/5)), (x+w-int(w/5), y-int(pivot_img_size/3)), info_box_color, cv2.FILLED)
								
								cv2.putText(img, analysis_report, (x+int(w/3.5), y - int(pivot_img_size/2.1)), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 111, 255), 2)
							
							#bottom
							elif y + h + pivot_img_size - int(pivot_img_size/5) < resolution_y:
							
								triangle_coordinates = np.array( [
									(x+int(w/2), y+h)
									, (x+int(w/2)-int(w/10), y+h+int(pivot_img_size/3))
									, (x+int(w/2)+int(w/10), y+h+int(pivot_img_size/3))
								] )
								
								cv2.drawContours(img, [triangle_coordinates], 0, info_box_color, -1)
								
								cv2.rectangle(img, (x+int(w/5), y + h + int(pivot_img_size/3)), (x+w-int(w/5), y+h+pivot_img_size-int(pivot_img_size/5)), info_box_color, cv2.FILLED)
								
								cv2.putText(img, analysis_report, (x+int(w/3.5), y + h + int(pivot_img_size/1.5)), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 111, 255), 2)
								
						#-------------------------------
						#face recognition
						
						custom_face = functions.preprocess_face(img = custom_face, target_size = (input_shape_y, input_shape_x), enforce_detection = False)
						
						#check preprocess_face function handled
						if custom_face.shape[1:3] == input_shape:
							if df.shape[0] > 0: #if there are images to verify, apply face recognition
								img1_representation = model.predict(custom_face)[0,:]
								
								#print(freezed_frame," - ",img1_representation[0:5])
								
								def findDistance(row):
									distance_metric = row['distance_metric']
									img2_representation = row['feature']
									
									distance = 1000 #initialize very large value
									if distance_metric == 'cosine':
										distance = dst.findCosineDistance(img1_representation, img2_representation)
									elif distance_metric == 'euclidean':
										distance = dst.findEuclideanDistance(img1_representation, img2_representation)
									elif distance_metric == 'euclidean_l2':
										distance = dst.findEuclideanDistance(dst.l2_normalize(img1_representation), dst.l2_normalize(img2_representation))
										
									return distance
								
								df['distance'] = df.apply(findDistance, axis = 1)
								df = df.sort_values(by = ["distance"])
								
								candidate = df.iloc[0]
								employee_name = candidate['employee']
								best_distance = candidate['distance']
								
								#print(candidate[['employee', 'distance']].values)
								print("""
									Best distance: %s
									Threshold: %s
									Is better: %s
								""" %(str(best_distance), str(threshold), str(best_distance<=threshold)))
								#if True:
								if best_distance <= threshold:
									#print(employee_name)
									display_img = cv2.imread(employee_name)
									
									display_img = cv2.resize(display_img, (pivot_img_size, pivot_img_size))
																		
									label = employee_name.split("/")[-1].replace(".jpg", "")
									label = re.sub('[0-9]', '', label)
									
									try:
										if y - pivot_img_size > 0 and x + w + pivot_img_size < resolution_x:
											#top right
											img[y - pivot_img_size:y, x+w:x+w+pivot_img_size] = display_img
											
											overlay = img.copy(); opacity = 0.4
											cv2.rectangle(img,(x+w,y),(x+w+pivot_img_size, y+20),(46,200,255),cv2.FILLED)
											cv2.addWeighted(overlay, opacity, img, 1 - opacity, 0, img)
											
											cv2.putText(img, label, (x+w, y+10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
											
											#connect face and text
											cv2.line(img,(x+int(w/2), y), (x+3*int(w/4), y-int(pivot_img_size/2)),(67,67,67),1)
											cv2.line(img, (x+3*int(w/4), y-int(pivot_img_size/2)), (x+w, y - int(pivot_img_size/2)), (67,67,67),1)
											
										elif y + h + pivot_img_size < resolution_y and x - pivot_img_size > 0:
											#bottom left
											img[y+h:y+h+pivot_img_size, x-pivot_img_size:x] = display_img
											
											overlay = img.copy(); opacity = 0.4
											cv2.rectangle(img,(x-pivot_img_size,y+h-20),(x, y+h),(46,200,255),cv2.FILLED)
											cv2.addWeighted(overlay, opacity, img, 1 - opacity, 0, img)
											
											cv2.putText(img, label, (x - pivot_img_size, y+h-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
											
											#connect face and text
											cv2.line(img,(x+int(w/2), y+h), (x+int(w/2)-int(w/4), y+h+int(pivot_img_size/2)),(67,67,67),1)
											cv2.line(img, (x+int(w/2)-int(w/4), y+h+int(pivot_img_size/2)), (x, y+h+int(pivot_img_size/2)), (67,67,67),1)
											
										elif y - pivot_img_size > 0 and x - pivot_img_size > 0:
											#top left
											img[y-pivot_img_size:y, x-pivot_img_size:x] = display_img
											
											overlay = img.copy(); opacity = 0.4
											cv2.rectangle(img,(x- pivot_img_size,y),(x, y+20),(46,200,255),cv2.FILLED)
											cv2.addWeighted(overlay, opacity, img, 1 - opacity, 0, img)
											
											cv2.putText(img, label, (x - pivot_img_size, y+10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
											
											#connect face and text
											cv2.line(img,(x+int(w/2), y), (x+int(w/2)-int(w/4), y-int(pivot_img_size/2)),(67,67,67),1)
											cv2.line(img, (x+int(w/2)-int(w/4), y-int(pivot_img_size/2)), (x, y - int(pivot_img_size/2)), (67,67,67),1)
											
										elif x+w+pivot_img_size < resolution_x and y + h + pivot_img_size < resolution_y:
											#bottom right
											img[y+h:y+h+pivot_img_size, x+w:x+w+pivot_img_size] = display_img
											
											overlay = img.copy(); opacity = 0.4
											cv2.rectangle(img,(x+w,y+h-20),(x+w+pivot_img_size, y+h),(46,200,255),cv2.FILLED)
											cv2.addWeighted(overlay, opacity, img, 1 - opacity, 0, img)
											
											cv2.putText(img, label, (x+w, y+h-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
											
											#connect face and text
											cv2.line(img,(x+int(w/2), y+h), (x+int(w/2)+int(w/4), y+h+int(pivot_img_size/2)),(67,67,67),1)
											cv2.line(img, (x+int(w/2)+int(w/4), y+h+int(pivot_img_size/2)), (x+w, y+h+int(pivot_img_size/2)), (67,67,67),1)
									except Exception as err:
										print(str(err))

								else:
									print("Not recognized face")
						tic = time.time() #in this way, freezed image can show 5 seconds
						
						#-------------------------------
				
				time_left = int(time_threshold - (toc - tic) + 1)
				
				cv2.rectangle(img, (10, 10), (90, 50), (67,67,67), -10)
				cv2.putText(img, str(time_left), (40, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)

				cv2.imshow('img', img)
				
				freezed_frame = freezed_frame + 1
			else:
				face_detected = False
				face_included_frames = 0
				freeze = False
				freezed_frame = 0
			
		else:
			cv2.imshow('img',img)
		
		if cv2.waitKey(1) & 0xFF == ord('q'): #press q to quit
			break
		
	#kill open cv things		
	cap.release()
	cv2.destroyAllWindows()

def generate_feature(face_image, shape_y, shape_x, model):
	feature = []

	# detect and align face
	img = functions.preprocess_face(img = face_image, target_size = (shape_y, shape_x), enforce_detection = False)

	# find the vector representation of the image detected above
	img_representation = model.predict(img)[0,:]
	
	# save the image with the vector representation
	feature.append(face_image)
	feature.append(img_representation)

	return feature

def add_to_feature_dict(key, img_representation, feature_dict):
	if key in feature_dict:
		feature_dict[key].append(img_representation)
	else:
		feature_dict[key] = [img_representation]

def extracted_features_mean(feature_dict):
	feature_list = []

	for key in feature_dict:
		features = np.array(feature_dict[key])
		feature_list.append([key, np.mean(features, axis = 0)])
	
	return feature_list

def save_new_detected_face(new_face, folder_name = ""):
	dir_path = os.path.abspath("faces_database")

	if(folder_name == ""):
		folder_name = str(len(os.listdir(dir_path)) + 1)

	dir_path = os.path.join(dir_path, folder_name)

	if(not os.path.isdir(dir_path)):
		os.makedirs(dir_path)

	count = len(os.listdir(dir_path))%30 + 1

	cv2.imwrite(os.path.join(dir_path, str(folder_name)+str(count)+".jpg"), new_face)
	return folder_name

def count_faces(name):
	dir_path = os.path.abspath("faces_database")
	subdir_path = os.path.join(dir_path, name)

	if(os.path.isdir(subdir_path)):
		return len(os.listdir(subdir_path))
	else:
		return 0

def realtime_analysis(db_path, model_name, distance_metric, enable_face_analysis = False):
	
	input_shape = (224, 224)
	input_shape_x = input_shape[0]; input_shape_y = input_shape[1]
	
	text_color = (255,255,255)
	
	face_images = []
	#check passed db folder exists
	if os.path.isdir(db_path) == True:
		for r, d, f in os.walk(db_path): # r=root, d=directories, f = files
			for file in f:
				if ('.jpg' in file):
					#exact_path = os.path.join(r, file)
					exact_path = r + "/" + file
					#print(exact_path)
					face_images.append(exact_path)
					
	if len(face_images) == 0:
		print("WARNING: There is no image in this path ( ", db_path,") . Face recognition will not be performed.")
	
	#------------------------
	
	if len(face_images) > 0:
		if model_name == 'VGG-Face':
			print("Using VGG-Face model backend and", distance_metric,"distance.")
			model = VGGFace.loadModel()
			input_shape = (224, 224)	
		
		elif model_name == 'OpenFace':
			print("Using OpenFace model backend", distance_metric,"distance.")
			model = OpenFace.loadModel()
			input_shape = (96, 96)
		
		elif model_name == 'Facenet':
			print("Using Facenet model backend", distance_metric,"distance.")
			model = Facenet.loadModel()
			input_shape = (160, 160)
		
		elif model_name == 'DeepFace':
			print("Using FB DeepFace model backend", distance_metric,"distance.")
			model = FbDeepFace.loadModel()
			input_shape = (152, 152)
		
		elif model_name == 'DeepID':
			print("Using DeepID model backend", distance_metric,"distance.")
			model = DeepID.loadModel()
			input_shape = (55, 47)
		
		elif model_name == 'Dlib':
			print("Using Dlib model backend", distance_metric,"distance.")
			from deepface.basemodels.DlibResNet import DlibResNet
			model = DlibResNet()
			input_shape = (150, 150)
		
		else:
			raise ValueError("Invalid model_name passed - ", model_name)
		#------------------------
		
		input_shape_x = input_shape[0]
		input_shape_y = input_shape[1]
		
		#tuned thresholds for model and metric pair
		threshold = functions.findThreshold(model_name, distance_metric)
		
	#------------------------
	#facial attribute analysis models
		
	if enable_face_analysis == True:
		
		tic = time.time()
		
		emotion_model = Emotion.loadModel()
		print("Emotion model loaded")
		
		age_model = Age.loadModel()
		print("Age model loaded")
		
		gender_model = Gender.loadModel()
		print("Gender model loaded")
		
		toc = time.time()
		
		print("Facial attribute analysis models loaded in ",toc-tic," seconds")
	
	#------------------------
	
	#find features for employee list
	
	tic = time.time()
	
	pbar = tqdm(range(0, len(face_images)), desc='Finding features')
	
	feature_dict = {}

	for index in pbar:
		face_image = face_images[index]
		image_description = face_image.split("/")
		person_name = image_description[1]
		pbar.set_description("Finding feature for %s" % image_description[1])

		# detect and align face
		img = functions.preprocess_face(img = face_image, target_size = (input_shape_y, input_shape_x), enforce_detection = False)

		# find the vector representation of the image detected above
		img_representation = model.predict(img)[0,:]
		
		# save the image with the vector representation
		add_to_feature_dict(person_name, img_representation, feature_dict)

	avg_features = extracted_features_mean(feature_dict) # average the feature's values foreach detected face
	
	df = pd.DataFrame(avg_features, columns = ['face_image', 'feature'])
	df['distance_metric'] = distance_metric
	
	toc = time.time()
	
	print("features found for given data set in ", toc-tic," seconds")
	
	#-----------------------

	time_threshold = 5; frame_threshold = 5
	pivot_frame_size = 112 # face recognition result image
	n_undetected = 0
	#-----------------------

	
	opencv_path = functions.get_opencv_path()
	face_detector_path = opencv_path+"haarcascade_frontalface_default.xml"
	face_cascade = cv2.CascadeClassifier(face_detector_path)
	
	#-----------------------
	tic = time.time()

	cap = cv2.VideoCapture(0)

	while(True):
		ret, frame = cap.read()
		
		raw_frame = frame.copy()
		resolution = frame.shape
		
		resolution_x = frame.shape[1]
		resolution_y = frame.shape[0]

		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		faces = face_cascade.detectMultiScale(frame, 1.3, 5)

		detected_faces = []
		face_index = 0

		for (x,y,w,h) in faces:
			if w > 130: #discard small detected faces
				
				face_detected = True
				
				detected_face = frame[int(y):int(y+h), int(x):int(x+w)] #crop detected face
				
				#-------------------------------------
				
				detected_faces.append((x,y,w,h))
				face_index = face_index + 1
				
				#-------------------------------------	
				#face recognition
				
				custom_face = functions.preprocess_face(detected_face, target_size = (input_shape_y, input_shape_x), enforce_detection = False)
				
				#check preprocess_face function handled
				if custom_face.shape[1:3] == input_shape:
					if df.shape[0] > 0: #if there are images to verify, apply face recognition
						img1_representation = model.predict(custom_face)[0,:]
						
						#print(freezed_frame," - ",img1_representation[0:5])
						
						def findDistance(row):
							distance_metric = row['distance_metric']
							img2_representation = row['feature']
							
							distance = 1000 #initialize very large value
							if distance_metric == 'cosine':
								distance = dst.findCosineDistance(img1_representation, img2_representation)
							elif distance_metric == 'euclidean':
								distance = dst.findEuclideanDistance(img1_representation, img2_representation)
							elif distance_metric == 'euclidean_l2':
								distance = dst.findEuclideanDistance(dst.l2_normalize(img1_representation), dst.l2_normalize(img2_representation))
								
							return distance
						
						df['distance'] = df.apply(findDistance, axis = 1)
						df = df.sort_values(by = ["distance"])
						
						candidate = df.iloc[0]
						employee_name = candidate['face_image']
						best_distance = candidate['distance']
						best_candidate = candidate['face_image']
						
						print("""
							Best distance: %s
							Threshold: %s
							Is better: %s
						""" 
						%(str(best_distance), str(threshold), str(best_distance<=threshold))
						)
						try: 
							if best_distance <= threshold: # if I found a known face --> green frame around it													
								label = employee_name.split("/")[-1].replace(".jpg", "")
								label = re.sub('[0-9]', '', label)	
								label = label.upper()
								cv2.rectangle(frame, (x,y), (x+w,y+h), (51, 204, 51), 2)

								quarter_w = int(w/4)

								overlay = frame.copy(); opacity = 0.4
								cv2.rectangle(frame,(x+quarter_w,y),(x+quarter_w+pivot_frame_size, y+20), (46,200,255) ,cv2.FILLED)
								cv2.addWeighted(overlay, opacity, frame, 1 - opacity, 0, frame)
									
								cv2.putText(frame, label, (x+quarter_w, y+15), cv2.FONT_HERSHEY_TRIPLEX, 0.5, text_color, 1)

								n_undetected = 0
								new_face = frame_cpy[y:y+h,x:x+w]
								save_new_detected_face(new_face, best_candidate)

							else: # if I didn't find a known face --> red frame around it
								frame_cpy = frame.copy()
								cv2.rectangle(frame, (x,y), (x+w,y+h), (0, 0, 179), 2)
								label = "UNKNOWN"
								quarter_w = int(w/4)

								overlay = frame.copy(); opacity = 0.4
								cv2.rectangle(frame,(x+quarter_w,y),(x+quarter_w+pivot_frame_size, y+20), (46,200,255) ,cv2.FILLED)
								cv2.addWeighted(overlay, opacity, frame, 1 - opacity, 0, frame)
									
								cv2.putText(frame, label, (x+quarter_w, y+15), cv2.FONT_HERSHEY_TRIPLEX, 0.5, text_color, 1)

								if(n_undetected > 20):
									new_face = frame_cpy[y:y+h,x:x+w]
									folder_name = save_new_detected_face(new_face, input("Not Recognized. Type a Name--> "))

									img = functions.preprocess_face(img = new_face, target_size = (input_shape_y, input_shape_x), enforce_detection = False)

									# find the vector representation of the image detected above
									new_face_representation = model.predict(img)[0,:]
									
									# save the image with the vector representation
									add_to_feature_dict(folder_name, new_face_representation, feature_dict)

									avg_features = extracted_features_mean(feature_dict) # average the feature's values foreach detected face
								
									df = pd.DataFrame(avg_features, columns = ['face_image', 'feature'])
									df['distance_metric'] = distance_metric	
									
								n_undetected += 1
						except Exception as err:
							print(str(err))

				tic = time.time() #in this way, freezed image can show 5 seconds

		cv2.imshow('img',frame)
		
		if cv2.waitKey(1) & 0xFF == ord('q'): #press q to quit
			break
		
	#kill open cv things		
	cap.release()
	cv2.destroyAllWindows()