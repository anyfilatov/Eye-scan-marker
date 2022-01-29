import struct

import numpy as np
from tkinter import *
from tkinter import filedialog
import PIL.Image, PIL.ImageTk, PIL.ImageDraw, PIL.ImageOps
import os


def interpolate_2_columns(two_cols, number_of_inserted):
    assert (np.shape(two_cols)[1] == 2)
    res = np.zeros((np.shape(two_cols)[0], number_of_inserted + 2))
    res[:, 0] = two_cols[:, 0]
    res[:, number_of_inserted + 1] = two_cols[:, 1]
    delta_col = (two_cols[:, 1] - two_cols[:, 0]) / (number_of_inserted + 1)
    for i in range(1, number_of_inserted + 1):
        res[:, i] = res[:, i - 1] + delta_col
    return res


def make_fat_img(thin_img, multiplier):
    thin_rows = np.shape(thin_img)[0]
    thin_cols = np.shape(thin_img)[1]
    fat_img = np.zeros((thin_rows, thin_cols * multiplier))
    for i in range(thin_cols - 1):
        fat_img[:, multiplier * i: multiplier * (i + 1) + 1] = interpolate_2_columns(thin_img[:, i:i + 2],
                                                                                     multiplier - 1)
    return fat_img


def read_new_array_form_file(file):
    rows = 400
    cols = int(512 * 500 // rows)
    cur_img = np.zeros((rows, cols))

    for i in range(rows):
        for j in range(cols):
            four_bytes = file.read(4)
            data = struct.unpack('f', four_bytes)[0]
            data = (2 * data - 1400) / 2500  # волшебные преобразования, чтобы сделать картинку более контрастной

            cur_img[rows - i - 1][cols - j - 1] = data

    img_x5 = make_fat_img(np.transpose(cur_img), 4)
    return img_x5 * 255


class Drawer:
    def __init__(self, root):
        self.root = root
        self.root.title("Empty scan")
        self.brush = "red"
        self.brush_size = 5
        self.input_file_name = ''
        self.file = None
        self.array = []
        self.cur_img = None
        self.pil_img = None
        self.tk_img = None
        self.image = None
        self.img_index = 0

        self.canvas = Canvas(self.root, height=640, width=1600)
        self.canvas.grid(row=3, column=0, columnspan=16, pady=10)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<Button-1>", self.draw)

        self.mask_pil = PIL.Image.new('RGB', (1600, 640), (255, 255, 255))
        self.mask_drawer = PIL.ImageDraw.Draw(self.mask_pil)

        self.id_label = Label(self.root, text='N/A')
        self.id_label.grid(row=1, column=3,pady=5)
        self.class1_btn = Button(self.root, text="PAMM (red)\nselected", width=10, command=lambda: self.set_brush("red"))
        self.class1_btn.grid(row=0, column=3, pady=5)
        self.class2_btn = Button(self.root, text="DRIL (green)", width=10, command=lambda: self.set_brush("green"))
        self.class2_btn.grid(row=0, column=4, pady=5)
        self.class3_btn = Button(self.root, text="IRNFL (blue)", width=10, command=lambda: self.set_brush("blue"))
        self.class3_btn.grid(row=0, column=5, pady=5)

        self.prev_btn = Button(self.root, text="<", width=5, command=lambda: self.goto_prev_img())
        self.prev_btn.grid(row=1, column=0)
        self.next_btn = Button(self.root, text=">", width=5, command=lambda: self.goto_next_img())
        self.next_btn.grid(row=1, column=5)

        self.browse_btn = Button(self.root, text="Browse the .OCT file", width=18, command=lambda: self.open_file())
        self.browse_btn.grid(row=0, column=0, pady=5)
        self.save_btn = Button(self.root, text="Save only mask", width=70,
                               command=lambda: self.save_img_to_file(str(self.img_index)))
        self.save_btn.grid(row=0, column=8)
        self.save_btn_full = Button(self.root, text="Save mask and image with mask", width=70,
                               command=lambda: self.save_united_img_mask(str(self.img_index)))
        self.save_btn_full.grid(row=1, column=8)

    def set_brush(self, color):
        self.brush = color
        if color == 'red':
            self.class1_btn.config(text='PAMM (red)\nselected')
            self.class2_btn.config(text='DRIL (green)')
            self.class3_btn.config(text='IRNFL (blue)')
        elif color == 'green':
            self.class1_btn.config(text='PAMM (red)')
            self.class2_btn.config(text='DRIL (green)\nselected')
            self.class3_btn.config(text='IRNFL (blue)')
        else:
            self.class1_btn.config(text='PAMM (red)')
            self.class2_btn.config(text='DRIL (green)')
            self.class3_btn.config(text='IRNFL (blue)\nselected')

    def draw(self, event):
        self.mask_drawer.ellipse((event.x - self.brush_size,
                                  event.y - self.brush_size,
                                  event.x + self.brush_size,
                                  event.y + self.brush_size),
                                 fill=self.brush, outline=self.brush)
        self.canvas.create_oval(event.x - self.brush_size,
                                event.y - self.brush_size,
                                event.x + self.brush_size,
                                event.y + self.brush_size,
                                fill=self.brush, outline=self.brush)

    def clear_area(self):
        self.canvas.delete('all')
        self.mask_drawer.rectangle((0, 0, 1600, 640), fill='white')

    def make_canvas_img_from_array(self, img_arr):
        self.pil_img = PIL.Image.fromarray(img_arr)
        self.tk_img = PIL.ImageTk.PhotoImage(self.pil_img)

        self.clear_area()
        self.image = self.canvas.create_image(0, 0, anchor=NW, image=self.tk_img)

    def goto_img_by_id(self, index):
        assert (len(self.array) >= index)
        self.id_label.config(text=str(index) + '/399')
        if len(self.array) == index:
            self.cur_img = read_new_array_form_file(self.file)
            self.array.append(self.cur_img)
        else:
            self.cur_img = self.array[index]

        self.make_canvas_img_from_array(self.cur_img)

    def goto_next_img(self):
        if self.img_index == 399 or self.input_file_name == '':
            return
        self.img_index += 1
        self.goto_img_by_id(self.img_index)

    def goto_prev_img(self):
        if self.img_index == 0 or self.input_file_name == '':
            return
        self.img_index -= 1
        self.goto_img_by_id(self.img_index)

    def save_img_to_file(self, filename):
        if self.input_file_name == '':
            print('Choose a file before saving')
            return
        self.mask_pil.save(self.out_dir + '/' + filename + '.png', format='png')
        print('Image ' + self.out_dir + '/' + filename + '.png saved')

    def save_united_img_mask(self, filename):
        if self.input_file_name == '':
            print('Choose a file before saving')
            return

        gray_mask = PIL.ImageOps.invert(self.mask_pil.convert('L'))
        gray_mask = gray_mask.point(lambda p: p > 150 and 255)

        rgb_img = PIL.Image.new("RGB", self.pil_img.size)
        rgb_img.paste(self.pil_img)
        rgb_img.paste(self.mask_pil, (0,0), gray_mask)
        rgb_img.save(self.out_dir + '/' + filename + '_full.png', format='png')
        print('Image ' + self.out_dir + '/' + filename + '_full.png saved')

        self.mask_pil.save(self.out_dir + '/' + filename + '.png', format='png')
        print('Image ' + self.out_dir + '/' + filename + '.png saved')

    def open_file(self):
        self.clear_area()
        self.input_file_name = filedialog.askopenfilename()
        self.file = open(self.input_file_name, 'rb')
        self.array = [read_new_array_form_file(self.file)]
        self.cur_img = self.array[0]
        self.make_canvas_img_from_array(self.cur_img)
        self.root.title(self.input_file_name.split('/')[-1])
        self.id_label.config(text='0/399')
        self.out_dir = self.input_file_name.split('.OCT')[0]
        try:
            os.mkdir(self.out_dir)
        except FileExistsError:
            return

    def on_close(self):
        # self.save_img_to_file(str(self.img_index))
        self.root.destroy()


root = Tk()
app = Drawer(root)
root.protocol("WM_DELETE_WINDOW", app.on_close)
root.mainloop()
