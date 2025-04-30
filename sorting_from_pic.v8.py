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
        self.selection_mode = False
        self.selected_indices = set()

        self.canvas = Canvas(root, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Configure>", lambda event: self.draw_images())
        self.canvas.bind("<Double-1>", self.on_double_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.root.bind("<Delete>", self.batch_delete_selected)

        self.load_button = tk.Button(root, text="Add Images", command=self.add_images)
        self.load_button.pack(side=tk.LEFT)
        self.clear_button = tk.Button(root, text="Clear Images", command=self.clear_images)
        self.clear_button.pack(side=tk.LEFT)
        self.paste_button = tk.Button(root, text="Paste File Names", command=self.paste_file_names)
        self.paste_button.pack(side=tk.LEFT)
        self.select_button = tk.Button(root, text="Selection Mode", command=self.toggle_selection_mode)
        self.select_button.pack(side=tk.LEFT)
        self.undo_button = tk.Button(root, text="Undo", command=self.undo_last_action)
        self.undo_button.pack(side=tk.LEFT)
        self.save_button = tk.Button(root, text="Save Order", command=self.save_order)
        self.save_button.pack(side=tk.RIGHT)

        self.positions = []
        self.drag_data = {"widget": None, "index": None, "image_id": None, "preview": None, "moved": False}
        self.navision_log = []
        self.undo_stack = []
        self.drag_outline = None

    def toggle_selection_mode(self):
        self.selection_mode = not self.selection_mode
        self.select_button.config(relief=tk.SUNKEN if self.selection_mode else tk.RAISED)
        if not self.selection_mode:
            self.selected_indices.clear()
            self.draw_images()

    def add_images(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("Image files", "*.png")])
        self.load_from_paths(file_paths, clear=False)

    def clear_images(self):
        self.image_paths.clear()
        self.images.clear()
        self.thumbnails.clear()
        self.positions.clear()
        self.selected_indices.clear()
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
            self.selected_indices.clear()
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
        self.root.update_idletasks()
        width = self.canvas.winfo_width()
        cols = max(1, (width - 20) // 60)
        padding = 20
        overlap = 60
        for i, thumb in enumerate(self.thumbnails):
            x = (i % cols) * (120 - overlap) + padding
            y = (i // cols) * (120 + padding) + padding
            img_id = self.canvas.create_image(x, y, anchor=tk.NW, image=thumb)
            if i in self.selected_indices:
                self.canvas.create_rectangle(x, y, x + 120, y + 120, outline="blue", width=2)
            self.positions.append((x, y, img_id))

    def get_image_index_at(self, x, y):
        for i in reversed(range(len(self.positions))):
            img_x, img_y, _ = self.positions[i]
            if img_x <= x <= img_x + 120 and img_y <= y <= img_y + 120:
                return i
        return None

    def on_press(self, event):
        index = self.get_image_index_at(event.x, event.y)
        if index is not None:
            ctrl_held = (event.state & 0x0004) != 0
            if self.selection_mode:
                if ctrl_held:
                    if index in self.selected_indices:
                        self.selected_indices.remove(index)
                    else:
                        self.selected_indices.add(index)
                    self.draw_images()
                    return
                else:
                    if index not in self.selected_indices:
                        self.selected_indices = {index}
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

            index = self.drag_data.get("index")
            if index is not None:
                self.show_drag_preview(index, preview_x, preview_y)

            if self.drag_outline:
                self.canvas.delete(self.drag_outline)
            self.drag_outline = self.canvas.create_rectangle(
                preview_x, preview_y, preview_x + 120, preview_y + 120,
                outline="red", width=2, dash=(4, 2)
            )

    def on_release(self, event):
        if self.drag_data["index"] is None:
            return

        from_index = self.drag_data["index"]
        to_index = self.get_image_index_at(event.x, event.y)

        if to_index is not None:
            self.undo_stack.append((self.image_paths.copy(), self.images.copy(), self.thumbnails.copy()))

            if self.selection_mode and self.selected_indices:
                selected = sorted(self.selected_indices)
                items = [(self.image_paths[i], self.images[i], self.thumbnails[i]) for i in selected]
                for i in reversed(selected):
                    del self.image_paths[i]
                    del self.images[i]
                    del self.thumbnails[i]
                insert_at = to_index if to_index < len(self.image_paths) else len(self.image_paths)
                for offset, (path, img, thumb) in enumerate(items):
                    self.image_paths.insert(insert_at + offset, path)
                    self.images.insert(insert_at + offset, img)
                    self.thumbnails.insert(insert_at + offset, thumb)
                self.selected_indices = set(range(insert_at, insert_at + len(items)))
            elif from_index != to_index:
                item = self.thumbnails.pop(from_index)
                path = self.image_paths.pop(from_index)
                img = self.images.pop(from_index)
                self.thumbnails.insert(to_index, item)
                self.images.insert(to_index, img)
                self.image_paths.insert(to_index, path)

        if self.drag_data["preview"]:
            self.canvas.delete(self.drag_data["preview"])
        if self.drag_outline:
            self.canvas.delete(self.drag_outline)
            self.drag_outline = None

        self.draw_images()
        self.drag_data = {"widget": None, "index": None, "image_id": None, "preview": None, "moved": False}

    def show_drag_preview(self, index, x, y):
        try:
            img = self.images[index].copy().convert("RGBA")
            img = img.resize((120, 120))

            # Brighten visible parts while keeping transparent background
            r, g, b, a = img.split()
            r = r.point(lambda i: min(255, i * 1.3))
            g = g.point(lambda i: min(255, i * 1.3))
            b = b.point(lambda i: min(255, i * 1.3))
            brightened = Image.merge("RGBA", (r, g, b, a))

            self.preview_img = ImageTk.PhotoImage(brightened)
            if self.drag_data["preview"]:
                self.canvas.coords(self.drag_data["preview"], x, y)
                self.canvas.itemconfig(self.drag_data["preview"], image=self.preview_img)
            else:
                self.drag_data["preview"] = self.canvas.create_image(x, y, image=self.preview_img)
        except Exception as e:
            print(f"Preview error: {e}")

    def undo_last_action(self):
        if self.undo_stack:
            paths, imgs, thumbs = self.undo_stack.pop()
            self.image_paths = list(paths)
            self.images = list(imgs)
            self.thumbnails = list(thumbs)
            self.draw_images()

    def on_double_click(self, event):
        index = self.get_image_index_at(event.x, event.y)
        if index is not None:
            self.show_full_image(index)

    def show_full_image(self, index):
        try:
            full_img = Image.open(self.image_paths[index])
            win = tk.Toplevel(self.root)
            win.title(os.path.basename(self.image_paths[index]))
            photo = ImageTk.PhotoImage(full_img)
            label = tk.Label(win, image=photo)
            label.image = photo
            label.pack()
        except Exception as e:
            print(f"Error loading full image: {e}")

    def on_right_click(self, event):
        index = self.get_image_index_at(event.x, event.y)
        if index is not None:
            confirm = messagebox.askyesno("Delete Image", "Do you want to delete this image?")
            if confirm:
                self.undo_stack.append((self.image_paths.copy(), self.images.copy(), self.thumbnails.copy()))
                del self.image_paths[index]
                del self.images[index]
                del self.thumbnails[index]
                self.draw_images()

    def batch_delete_selected(self, event=None):
        if not self.selected_indices:
            return
        confirm = messagebox.askyesno("Batch Delete", "Delete all selected images?")
        if confirm:
            self.undo_stack.append((self.image_paths.copy(), self.images.copy(), self.thumbnails.copy()))
            for index in sorted(self.selected_indices, reverse=True):
                del self.image_paths[index]
                del self.images[index]
                del self.thumbnails[index]
            self.selected_indices.clear()
            self.draw_images()

    def save_order(self):
        if not self.image_paths:
            return
        save_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text file", "*.txt")])
        if save_path:
            with open(save_path, "w") as f:
                for path in self.image_paths:
                    filename = os.path.splitext(os.path.basename(path))[0]
                    f.write(f"{filename}\n")
            print(f"\u2705 Sorted order saved to {save_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageSorterApp(root)
    root.mainloop()
