import tkinter as tk
from tkinter import filedialog, Canvas, Text, messagebox
from PIL import Image, ImageTk
import os

class ImageSorterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cushion Cover Sorter")

        self.image_paths = []
        self.images = []
        self.thumbnails = []
        self.canvas = Canvas(root, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        self.load_button = tk.Button(root, text="Add Images", command=self.add_images)
        self.load_button.pack(side=tk.LEFT)
        self.clear_button = tk.Button(root, text="Clear Images", command=self.clear_images)
        self.clear_button.pack(side=tk.LEFT)
        self.paste_button = tk.Button(root, text="Paste File Names", command=self.paste_file_names)
        self.paste_button.pack(side=tk.LEFT)
        self.save_button = tk.Button(root, text="Save Order", command=self.save_order)
        self.save_button.pack(side=tk.RIGHT)

        self.positions = []
        self.drag_data = {"widget": None, "index": None, "image_id": None, "preview": None, "moved": False}
        self.navision_log = []

    def add_images(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("Image files", "*.png")])
        self.load_from_paths(file_paths, clear=False)

    def clear_images(self):
        self.image_paths.clear()
        self.images.clear()
        self.thumbnails.clear()
        self.positions.clear()
        self.canvas.delete("all")

    def paste_file_names(self):
        input_window = tk.Toplevel(self.root)
        input_window.title("Paste File Names")
        tk.Label(input_window, text="Paste filenames (one per line, no extension):").pack()
        text_box = Text(input_window, width=50, height=20)
        text_box.pack()
        tk.Button(input_window, text="Load", command=lambda: self.load_from_pasted(text_box.get("1.0", tk.END), input_window)).pack()

    def load_from_pasted(self, text, window):
        folder_path = filedialog.askdirectory(title="Select Folder Containing PNG Files")
        if not folder_path:
            return

        file_names = [line.strip() + ".png" for line in text.strip().splitlines() if line.strip()]
        file_paths = []
        self.navision_log = []

        for name in file_names:
            full_path = os.path.join(folder_path, name)
            if os.path.exists(full_path):
                file_paths.append(full_path)
            else:
                self.navision_log.append(name.replace(".png", ""))

        if not file_paths:
            messagebox.showwarning("Warning", "No matching files found.")
            return

        window.destroy()
        self.load_from_paths(file_paths, clear=False)
        if self.navision_log:
            self.show_navision_log()

    def show_navision_log(self):
        nav_window = tk.Toplevel(self.root)
        nav_window.title("Missing Files")
        tk.Label(nav_window, text="These files were not found:").pack()
        text_area = Text(nav_window, width=50, height=20)
        text_area.pack()
        for name in self.navision_log:
            text_area.insert(tk.END, f"{name}\n")
        text_area.config(state=tk.DISABLED)

    def load_from_paths(self, file_paths, clear=True):
        if clear:
            self.image_paths = list(file_paths)
            self.images.clear()
            self.thumbnails.clear()
            self.canvas.delete("all")
            self.positions.clear()
        else:
            self.image_paths.extend(file_paths)

        for path in file_paths:
            try:
                img = Image.open(path).convert("RGBA")
                img.thumbnail((120, 120))
                self.thumbnails.append(ImageTk.PhotoImage(img))
                self.images.append(img)
            except Exception as e:
                print(f"Error loading {path}: {e}")

        self.draw_images()

    def draw_images(self):
        self.canvas.delete("all")
        self.positions.clear()
        cols = 25
        padding = 20
        overlap = 60
        for i, thumb in enumerate(self.thumbnails):
            x = (i % cols) * (120 - overlap) + padding
            y = (i // cols) * (120 + padding) + padding
            img_id = self.canvas.create_image(x, y, anchor=tk.NW, image=thumb)
            self.positions.append((x, y, img_id))

    def get_image_index_at(self, x, y):
        for i in reversed(range(len(self.positions))):
            img_x, img_y, _ = self.positions[i]
            if img_x <= x <= img_x + 60 and img_y <= y <= img_y + 120:
                return i
        return None

    def on_press(self, event):
        index = self.get_image_index_at(event.x, event.y)
        if index is not None:
            self.drag_data["index"] = index
            self.drag_data["widget"] = self.thumbnails[index]
            self.drag_data["moved"] = False
            self.show_drag_preview(index, event.x, event.y)

    def on_drag(self, event):
        if self.drag_data["preview"]:
            x, y = event.x, event.y
            preview_x = max(0, x)
            preview_y = max(0, y)
            self.drag_data["moved"] = True

            overlapping_zone = False
            for img_x, img_y, _ in self.positions:
                if img_x <= x <= img_x + 60 and img_y <= y <= img_y + 120:
                    overlapping_zone = True
                    break

            index = self.drag_data.get("index")
            if index is not None:
                img = self.images[index].copy()
                size = (120, 120) if overlapping_zone else (180, 180)
                img = img.resize(size)
                self.preview_img = ImageTk.PhotoImage(img)
                self.canvas.itemconfig(self.drag_data["preview"], image=self.preview_img)
                self.canvas.coords(self.drag_data["preview"], preview_x, preview_y)

    def on_release(self, event):
        if self.drag_data["index"] is None:
            return

        from_index = self.drag_data["index"]
        to_index = self.get_image_index_at(event.x, event.y)

        if to_index is not None and from_index != to_index:
            item = self.thumbnails.pop(from_index)
            path = self.image_paths.pop(from_index)
            thumb = item
            img = self.images.pop(from_index)
            self.thumbnails.insert(to_index, thumb)
            self.images.insert(to_index, img)
            self.image_paths.insert(to_index, path)

        if self.drag_data["preview"]:
            self.canvas.delete(self.drag_data["preview"])

        self.draw_images()
        self.drag_data = {"widget": None, "index": None, "image_id": None, "preview": None, "moved": False}

    def show_drag_preview(self, index, x, y):
        try:
            img = self.images[index].copy()
            img = img.resize((120, 120))
            self.preview_img = ImageTk.PhotoImage(img)
            self.drag_data["preview"] = self.canvas.create_image(x, y, image=self.preview_img)
        except Exception as e:
            print(f"Preview error: {e}")

    def save_order(self):
        if not self.image_paths:
            return
        save_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text file", "*.txt")])
        if save_path:
            with open(save_path, "w") as f:
                for path in self.image_paths:
                    filename = os.path.splitext(os.path.basename(path))[0]
                    f.write(f"{filename}\n")
            print(f"✅ Sorted order saved to {save_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageSorterApp(root)
    root.mainloop()
