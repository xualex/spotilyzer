import requests
import pandas as pd
from sklearn import preprocessing
import itertools
import numpy as np
from scipy.spatial.distance import pdist, squareform
import random
import time

#This just gets rid of the warnings that have been annoying me
import warnings
warnings.filterwarnings("ignore")


#Normalize data frame where song features are stored
def normalizeDf(df):
	min_max_scaler = preprocessing.MinMaxScaler()
	for i in allFeatures: #Change for general df
		df[i] = pd.DataFrame(min_max_scaler.fit_transform(df[i]))
	return df.set_index("songid")


#Creates an n*n array that corresponds to weights on how close 2 songs are
#The ith row and jth column corresponds to relation from the ith song to the jth song
def createWeightArray(df):
    weightArray = np.zeros((df.shape[0],df.shape[0]))
    #Probabilistic weight for song i -> song j
    for i in range(df.shape[0]):
        for j in range(df.shape[0]):
            weightArray[i][j] = songWeight(df.ix[i],df.ix[j])
            if (i == j):
                weightArray[i][j] = 0
    return weightArray

#Given those variables, it creates an array where the ith position is the chance the current song goes to song i
def create1DWeightArrayLin(df, currSong, finalSong, time):
	weightArrayLin = np.zeros(df.shape[0])
	for i in range(df.shape[0]):
		weightArrayLin[i] = songWeightLin(currSong, df.ix[i], finalSong, time)
	return weightArrayLin


#Gives a weight for song1 -> song2 based off of their distance. Song 1 and 2 are arrays of numbers.
#TODO add different weight functions
def songWeight(song1,song2):
    dist = pdist([song1,song2],'minkowski',1)[0] #taxicab
    return max(1.5-dist,0)

#Gives a weight for song1 -> song2. The algorithm is pretty random
def songWeightLin(currSong, nextSong, finalSong, time): #Time = 0 means that this is the last step
	#Song cant go right back to itself
	if currSong.ix == nextSong.ix:
		return 0

	# SD and µ for all the different metrics
	standardDeviations = np.zeros(currSong.size)
	means = np.zeros(currSong.size)

	for i in range (0, currSong.size):
		#this is just some bad formula that should make something that sorta goes from one song to another
		#it should definitely be changed
		means[i] = currSong[i] + (currSong[i] - finalSong[i]) / time
		standardDeviations[i] = np.abs((currSong[i] - finalSong[i]) / time)

	#Calculates pdf given all the variables
	def calcPDF(val, mean, sd):
		#Gets rid of some infinity problem im too lazy to figure out
		if sd == 0:
			return 0
		return np.exp(-1*(val - mean)**2/(2*sd**2))/np.sqrt(2*np.pi*sd**2)

	#Array contains all the different PDFs for all the metrics
	pdfVals = np.zeros(currSong.size)
	for i in range (0, currSong.size):
		pdfVals[i] = calcPDF(nextSong[i], means[i], standardDeviations[i])

	return sum(pdfVals)#figure this out too


#Gives a random walk over k steps. Will not repeat the last r responses.
#Array needs to be n*n and r<n.
def randomWalk(weightArray, startIndex=0, k=100, r=0):
    walkPath = np.zeros((k,), dtype=np.int)
    walkPath[0] = startIndex
    for i  in range(1,k):
        walkWeights = weightArray[int(walkPath[i-1])]
        #Remove last r songs
        for j in range(max(i-r,0),i):
            walkWeights[walkPath[j]] = 0
        walkPath[i] = weightedChoice(walkWeights)
    return walkPath

#Gives a random walk with t time. It can repeat songs still, weightArrayLin is the thing generated by create1DWeightArrayLin
def randomWalkLin(weightArrayLin, startIndex=0, endIndex=100, t=10):
	walkPath = np.zeros((t,), dtype=np.int)

	#First song should be start song, last song should be end song
	walkPath[0] = startIndex
	walkPath[-1] = endIndex
	for i in range(1,t-1):
		walkPath[i] = weightedChoice(weightArrayLin)
	return walkPath

#Defines a choce function given weights. TODO make more varied weight functions
def weightedChoice(weights):
    totalWeight = np.sum(weights)
    if totalWeight == 0:
        return random.randint(0,len(weights))
    #Subtract the weight from choice at each step and return the song it gets below 0 at
    choice = random.random() * totalWeight
    for i in range(len(weights)):
        choice -= weights[i]
        if choice <= 0:
            return i
    return len(weights) - 1


#Creates a song list given a random walk on df
def toSongList(randomWalk, df):
	songList = []
	for i in range(len(randomWalk)):
		songList += [df.ix[int(randomWalk[i])].name]
	return songList

#Turns a list of songs into a URI input
def toURI(songList):
    urisArray = []
    for songId in songList:
        songURI = 'spotify:track:' + songId
        urisArray += [songURI]
    return urisArray

#Turns a list of strings into a big string
def toString(List):
	line = ''
	for thing in List:
		line += thing + ','
	return line


# featuredPlaylists = requests.get("https://api.spotify.com/v1/browse/featured-playlists", headers=access_header).json()["playlists"]["items"]
# allFeaturedPlaylistData = {}
# for i in featuredPlaylists:
# 	tracks = requests.get(i["href"] + "/tracks", headers=access_header).json()["items"]
# 	tracksList = []
# 	for j in tracks:
# 		tracksList.append(j["track"]["id"])
# 	allFeaturedPlaylistData[i["id"]] = gd.getSongs(tracksList)


#To pass in data, pass in a df with song ids and normalized data
allFeatures = ["danceability", "energy", "key", "loudness", "speechiness", "acousticness",
				 "instrumentalness", "liveness", "valence", "tempo", "time_signature"]

df = pd.read_csv('../data/song_data.csv')
del df['category']
del df['popularity']
del df['song_title']
del df['artist_name']
ndf = normalizeDf(df)

wal = create1DWeightArrayLin(ndf.ix[:150], ndf.ix[0], ndf.ix[100], 10)
rwl = randomWalkLin(wal)
sl = toSongList(rwl, ndf)

print(sl)
print(rwl)

print("mean: ", np.mean(wal))
print("variance: ", np.var(wal))
print("elements > 0: ", len(wal[wal > 0]))



#Getting some demo code to run
wa = createWeightArray(ndf.ix[:150])
rw = randomWalk(wa, r = 10)
sl = toSongList(rw,ndf)
uriList = toURI(sl)
print(toString(uriList))

#print(sl)
#print(rw)

#print("mean: ", np.mean(wa))
#print("variance: ", np.var(wa))
#print("elements > 0: ", len(wa[wa > 0]))
