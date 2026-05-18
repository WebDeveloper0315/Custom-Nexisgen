import os
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import cv2

folder_path = ".nexis/miner/"

folder_path_of_jpgs = os.path.join(folder_path, "frames")
folder_path_of_json = os.path.join(folder_path, "info")
folder_path_of_videos = os.path.join(folder_path, "clips")


# Get all jpg and txt files
jpg_files = sorted([f for f in os.listdir(folder_path_of_jpgs) if f.endswith(".jpg")])
txt_files = sorted([f for f in os.listdir(folder_path_of_json) if f.endswith(".json")])

# Create dictionary {jpg: txt}
file_dict = {jpg: txt for jpg, txt in zip(jpg_files, txt_files)}

print(file_dict)


# Function to read txt
def read_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


class ImageViewer:
    def __init__(self, master, file_dict, folder_path):
        # FIRST
        self.master = master
        self.master.bind("<Down>", self.delete_image_key)
        self.master.bind("<Right>", self.next_image_key)
        self.master.bind("<Left>", self.before_image_key)

        # NOW self.master exists
        self.master.title("Image Viewer")

        self.master.geometry("1400x900")

        



        self.video_job = None
        self.folder_path = folder_path
        self.file_dict = file_dict
        self.keys = list(file_dict.keys())
        self.index = 0

        # video object
        self.cap = None
        

        self.right_frame = tk.Frame(master)
        self.right_frame.pack(side="right", padx=10, pady=10)

        self.master.bind("<Configure>", self.on_resize)

        self.counter_label = tk.Label(
            self.right_frame,
            text="0/0",
            font=("Arial", 14)
        )
        self.counter_label.pack(pady=10)


        # =========================
        # MAIN DISPLAY FRAME
        # =========================
        self.display_frame = tk.Frame(master)
        self.display_frame.pack(
            side="top",
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        # LEFT IMAGE
        self.img_label = tk.Label(self.display_frame)
        self.img_label.pack(
            side="left",
            expand=True,
            fill="both",
            padx=10
        )

        self.txt_frame = tk.Frame(self.display_frame)
        self.txt_frame.pack(side="left", padx=10, pady=10)

        self.txt_label = tk.Label(
            master,
            text="",
            justify="left",
            anchor="nw"
        )

        self.txt_label.pack(
            fill="x",
            padx=10,
            pady=10
        )   

        # RIGHT FRAMES
        self.video_frame = tk.Frame(self.display_frame)
        self.video_frame.pack(
            side="right",
            expand=True,
            fill="both",
            padx=10
        )

        self.frame1_label = tk.Label(self.video_frame)
        self.frame1_label.pack(expand=True, fill="both", pady=5)

        self.frame2_label = tk.Label(self.video_frame)
        self.frame2_label.pack(expand=True, fill="both", pady=5)

        self.frame3_label = tk.Label(self.video_frame)
        self.frame3_label.pack(expand=True, fill="both", pady=5)

        # TEXT
        # I need to align with left image and has to be located below the left image
        # For now this is aligned below images including left image and right video frames, so it is slipped down whenever the video frames are shown
        # I need to align it with the left image and make it fixed position below the left image
        # I need to make it fixed position below the left image and not slipped down whenever the video frames are shown

        # Create a new frame for the text and align it with the left image and make it fixed position below the left image  
        # This frame will be located below the left image and will be fixed position
        
       
# ///////////////////////////////////////////
        self.next_btn = tk.Button(
            self.right_frame,
            text="Next",
            command=self.next_image
        )
        self.next_btn.pack(pady=5)

        self.before_btn = tk.Button(
            self.right_frame,
            text="Before",
            command=self.before_image
        )
        self.before_btn.pack(pady=5)

        self.delete_btn = tk.Button(
            self.right_frame,
            text="Delete",
            command=self.delete_image
        )
        self.delete_btn.pack(pady=5)

        # self.show_image()
        self.master.after(200, self.show_image)


    def next_image_key(self, event):
        self.next_image()

    def delete_image_key(self, event):
        self.delete_image()

    def before_image_key(self, event):
        self.before_image()

    def on_resize(self, event):

        # prevent too many refreshes
        if event.widget == self.master:

            self.show_image()



    def get_video_frames(self, video_path):

        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            return [None, None, None]

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        fps = cap.get(cv2.CAP_PROP_FPS)

        if fps <= 0:
            fps = 30

        duration = total_frames / fps

        # -------------------------
        # target positions
        # -------------------------
        sec1 = 1
        middle_sec = duration / 2
        end_sec = max(duration - 1, 0)

        positions = [
            int(sec1 * fps),
            int(middle_sec * fps),
            int(end_sec * fps)
        ]

        frames = []

        for pos in positions:

            cap.set(cv2.CAP_PROP_POS_FRAMES, pos)

            ret, frame = cap.read()

            if ret:

                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                frame_width = max(self.video_frame.winfo_width(), 250)
                frame_height = max(int(self.video_frame.winfo_height() / 3), 150)

                frame = cv2.resize(frame, (frame_width, frame_height))
                img = Image.fromarray(frame)

                tk_img = ImageTk.PhotoImage(img)

                frames.append(tk_img)

            else:
                frames.append(None)

        cap.release()

        return frames



    def show_image(self):

        if not self.keys:
            self.img_label.config(image="")
            for label in (self.frame1_label, self.frame2_label, self.frame3_label):
                label.config(image="")
            self.txt_label.config(text="No files left!")
            return
        
        total_files = len(self.keys)
        current_file = self.index + 1

        self.counter_label.config(
            text=f"{current_file}/{total_files}"
        )

        # =========================
        # STOP OLD VIDEO LOOP
        # =========================
        if self.video_job is not None:
            self.master.after_cancel(self.video_job)
            self.video_job = None

        # release previous video
        if self.cap:
            self.cap.release()

        jpg_file = self.keys[self.index]
        txt_file = self.file_dict[jpg_file]

        # =========================
        # SHOW JPG
        # =========================
        jpg_path = os.path.join(folder_path_of_jpgs, jpg_file)

        img = Image.open(jpg_path)

        # get current label size
        label_width = self.img_label.winfo_width()
        label_height = self.img_label.winfo_height()

        # startup fallback size
        if label_width < 50:
            label_width = 500

        if label_height < 50:
            label_height = 400

        # keep aspect ratio
        img.thumbnail((label_width, label_height))

        self.tk_jpg = ImageTk.PhotoImage(img)

        self.img_label.config(image=self.tk_jpg)
        self.img_label.image = self.tk_jpg

        # =========================
        # SHOW TXT
        # =========================
        txt_path = os.path.join(folder_path_of_json, txt_file)

        text_content = read_txt(txt_path)

        self.txt_label.config(text=text_content)

        # =========================
        # LOAD VIDEO
        # =========================
        mp4_file = os.path.splitext(jpg_file)[0] + ".mp4"

        mp4_path = os.path.join(folder_path_of_videos, mp4_file)

        frames = self.get_video_frames(mp4_path)

        for label, frame in zip(
            (self.frame1_label, self.frame2_label, self.frame3_label),
            frames,
        ):
            if frame:
                label.config(image=frame)
                label.image = frame
            else:
                label.config(image="")

    def play_video(self):

        if self.cap is None:
            return

        ret, frame = self.cap.read()

        # restart video
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()

        if ret:

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            frame = cv2.resize(frame, (400, 300))

            img = Image.fromarray(frame)

            self.tk_video = ImageTk.PhotoImage(img)

            self.frame1_label.config(image=self.tk_video)
            self.frame1_label.image = self.tk_video

        # SAVE after() ID
        self.video_job = self.master.after(30, self.play_video)

    def next_image(self):

        if self.index < len(self.keys) - 1:
            self.index += 1
            self.show_image()

    def before_image(self):

        if self.index > 0:
            self.index -= 1
            self.show_image()

    def delete_image(self):

        if not self.keys:
            return

        jpg_file = self.keys.pop(self.index)
        txt_file = self.file_dict.pop(jpg_file)

        mp4_file = os.path.splitext(jpg_file)[0] + ".mp4"

        jpg_path = os.path.join(folder_path_of_jpgs, jpg_file)
        txt_path = os.path.join(folder_path_of_json, txt_file)
        mp4_path = os.path.join(folder_path_of_videos, mp4_file)

        for path in (jpg_path, txt_path, mp4_path):

            try:
                os.remove(path)

            except FileNotFoundError:
                pass

            except OSError as e:
                messagebox.showerror(
                    "Delete Error",
                    f"Could not delete {os.path.basename(path)}: {e}"
                )
                return

        if self.index >= len(self.keys):
            self.index = len(self.keys) - 1

        self.show_image()


# Run app
root = tk.Tk()

app = ImageViewer(root, file_dict, folder_path)

root.mainloop()