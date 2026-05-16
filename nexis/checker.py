import os
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import cv2

folder_path = "./data"

folder_path_of_jpgs = os.path.join(folder_path, "jpgs")
folder_path_of_txts = os.path.join(folder_path, "txts")
folder_path_of_videos = os.path.join(folder_path, "videos")


# Get all jpg and txt files
jpg_files = sorted([f for f in os.listdir(folder_path_of_jpgs) if f.endswith(".jpg")])
txt_files = sorted([f for f in os.listdir(folder_path_of_txts) if f.endswith(".txt")])

# Create dictionary {jpg: txt}
file_dict = {jpg: txt for jpg, txt in zip(jpg_files, txt_files)}

print(file_dict)


# Function to read txt
def read_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


class ImageViewer:
    def __init__(self, master, file_dict, folder_path):
        self.video_job = None
        self.master = master
        self.master.title("Image + Video Viewer")

        self.folder_path = folder_path
        self.file_dict = file_dict
        self.keys = list(file_dict.keys())
        self.index = 0

        # video object
        self.cap = None
        

        self.right_frame = tk.Frame(master)
        self.right_frame.pack(side="right", padx=10, pady=10)

        self.display_frame = tk.Frame(master)
        self.display_frame.pack(side="top", padx=10, pady=10)

        # LEFT = JPG
        self.img_label = tk.Label(self.display_frame)
        self.img_label.pack(side="left", padx=10)

        # RIGHT = VIDEO
        # =========================
        # RIGHT FRAME FOR 3 FRAMES
        # =========================
        self.video_frame = tk.Frame(self.display_frame)
        self.video_frame.pack(side="right", padx=10)

        self.frame1_label = tk.Label(self.video_frame)
        self.frame1_label.pack(pady=5)

        self.frame2_label = tk.Label(self.video_frame)
        self.frame2_label.pack(pady=5)

        self.frame3_label = tk.Label(self.video_frame)
        self.frame3_label.pack(pady=5)

        # TXT BELOW
        self.txt_label = tk.Label(
            master,
            text="",
            wraplength=800,
            justify="left"
        )
        self.txt_label.pack(pady=10)
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

                frame = cv2.resize(frame, (250, 150))

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
            self.video_label.config(image="")
            self.txt_label.config(text="No files left!")
            return

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
        img = img.resize((400, 300))

        self.tk_jpg = ImageTk.PhotoImage(img)

        self.img_label.config(image=self.tk_jpg)

        # =========================
        # SHOW TXT
        # =========================
        txt_path = os.path.join(folder_path_of_txts, txt_file)

        text_content = read_txt(txt_path)

        self.txt_label.config(text=text_content)

        # =========================
        # LOAD VIDEO
        # =========================
        mp4_file = os.path.splitext(jpg_file)[0] + ".mp4"

        mp4_path = os.path.join(folder_path_of_videos, mp4_file)

        frames = self.get_video_frames(mp4_path)

        if frames[0]:
            self.frame1_label.config(image=frames[0])
            self.frame1_label.image = frames[0]

        if frames[1]:
            self.frame2_label.config(image=frames[1])
            self.frame2_label.image = frames[1]

        if frames[2]:
            self.frame3_label.config(image=frames[2])
            self.frame3_label.image = frames[2]

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

            self.video_label.config(image=self.tk_video)

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
        txt_path = os.path.join(folder_path_of_txts, txt_file)
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