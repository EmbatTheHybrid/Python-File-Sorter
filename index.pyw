import mimetypes
import os
import threading

from ctypes import windll
from shutil import rmtree
from time import sleep
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Constants
MAIN_FOLDER = "" # The folder you want this program to check
SORTING_FOLDER = "" # The folder where you want files to be sorted in

# This is relative to your sorting location. If you want images to go to your sorting folder's Pictures folder, give "Pictures" to an "image" key
CATEGORY_LOCATIONS = {
	"image": "",
	"text": "",
	"video": "",
	"audio": "",
	"application": "",
	"folder": ""
}

# Sorting requires that folders inside of the sorting folder be named accoridng to their category

# application, image, video, audio, font, text, model, multipart, example, message

# If you want folders to work with this, make a folder in the sorting folder named folders

# Are all possible names you can use for each folder
# If you want to be even more specific, you can sort with the file extension as well

# So if you want to put exe files in their own folder, have a folder in application named exe
# Refer to https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
# To know what category the most common file types are

zipExtensions = ["zip", "7z"]

mimetypes.init()

# Taken from stackoverflow
def is_file_copy_finished(file_path):
	if (not os.path.exists(file_path)):
		return

	finished = False

	GENERIC_WRITE         = 1 << 30
	FILE_SHARE_READ       = 0x00000001
	OPEN_EXISTING         = 3
	FILE_ATTRIBUTE_NORMAL = 0x80

	if not isinstance(file_path, str):
		file_path_unicode = file_path.decode('utf-8')
	else:
		file_path_unicode = file_path

	h_file = windll.Kernel32.CreateFileW(file_path_unicode, GENERIC_WRITE, FILE_SHARE_READ, None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None)

	if h_file != -1:
		windll.Kernel32.CloseHandle(h_file)
		finished = True

	print('is_file_copy_finished: ', str(finished), file_path)
	return finished

def wait_for_file_copy_finish(file_path):
    while not is_file_copy_finished(file_path):
        sleep(0.2)

def getTotalSize(filePath):
	size = 0
	for file in os.scandir(filePath):
		if (os.path.isfile(file)):
			wait_for_file_copy_finish(file.path)

		size += os.path.getsize(file) if os.path.isfile(file) else getTotalSize(file.path)

	return size

def moveFile(fileName, filePath):
	# Check if f ile exists
	if (not os.path.exists(filePath)):
		return
		
	# Check if it's a folder and a "folders" folder exists
	if (os.path.isdir(filePath) and os.path.exists(f"{SORTING_FOLDER}{CATEGORY_LOCATIONS['folder']}")):
		currentSize = -1
		totalSize = 0
		while (currentSize != totalSize):
			currentSize = totalSize

			sleep(2)
			totalSize = getTotalSize(filePath=filePath)

			print(currentSize, totalSize)	

		newPath = f"{SORTING_FOLDER}{CATEGORY_LOCATIONS['folder']}\\{fileName}"
		
		try:
			os.rename(filePath, newPath)
		except FileExistsError:
			print("Folder already exists, deleting and replacing with the new folder")
			rmtree(newPath)
			sleep(0.1)
			os.rename(filePath, newPath)
		
		for extension in zipExtensions:
			if (not os.path.exists(f"{MAIN_FOLDER}\\{fileName}.{extension}")):
				continue

			# Delete the zip file automatically
			print("Zip successfully deleted")
			os.remove(f"{MAIN_FOLDER}\\{fileName}.{extension}")

		return

	# Wait for copying to finish first
	wait_for_file_copy_finish(file_path=filePath)

	guess = mimetypes.guess_type(fileName)[0]

	if (guess is None):
		return

	category, fileType = guess.split("/")
	onlyName, fileExtension = fileName.rsplit(".", 1)
	print(category, fileType, fileExtension)

	directory = CATEGORY_LOCATIONS.get(category)
	if (directory is None):
		return

	if (fileExtension in ["docx", "doc", "pdf"]):
		print("In here")
		directory = CATEGORY_LOCATIONS.get('text')

	print(directory)

	location = f"{SORTING_FOLDER}{directory}\\"

	# If there's not folder for the category or it's being downloaded
	if (not os.path.exists(location)):
		return

	# If the file extension has its own folder
	if (os.path.exists(f"{location}{fileExtension}")):
		location = f"{location}{fileExtension}\\"

	location = f"{location}{onlyName}"
	
	# If file with the same name exists we add a number and try again until it works
	if (os.path.exists(f"{location}.{fileExtension}")):
		number = 2
		tempLocation = location
		location = f"{tempLocation} ({number})"
		while (os.path.exists(f"{location}.{fileExtension}")):
			number += 1
			location = f"{tempLocation} ({number})"

	os.rename(filePath, f"{location}.{fileExtension}")

def validateFile(event):
	filePath = event.src_path.strip()
	if (not MAIN_FOLDER in filePath): 
		return
	
	fileName = filePath.replace(MAIN_FOLDER, "")
	extension = fileName.lower().rsplit(".", 1)
	if (("download" in extension) or ("tmp" in extension)):
		return

	move = threading.Thread(target=moveFile, args=(fileName, filePath))
	move.start()

class MyHandler(FileSystemEventHandler):
	def on_modified(self, event):
		validateFile(event)
	def on_created(self, event):
		validateFile(event)

# Initally go through the folder first

def main():
	for file in os.scandir(MAIN_FOLDER):
		move = threading.Thread(target=moveFile, args=(file.name, file.path))
		move.start()

	event_handler = MyHandler()
	observer = Observer()
	observer.schedule(event_handler, path=MAIN_FOLDER, recursive=False)
	observer.start()

	while True:
		sleep(1)
		try:
			pass
		except KeyboardInterrupt:
			observer.stop()

if __name__ == "__main__":
	main()
