"""
Florence Nightingale's Rose Diagram - Display and print pixel coordinates when hovering/clicking on an image.
Enhanced with coordinate groups, history, file persistence, and drag mode.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import json
import os
from datetime import datetime


class ImageXYReader:
    def __init__(self, root):
        self.root = root
        self.root.title("Florence Nightingale's Rose Diagram")
        self.root.geometry("1200x700")
        
        # Initialize all coordinate variables FIRST (before creating UI)
        self.original_image = None
        self.image = None
        self.photo_image = None
        self.canvas_image = None
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.zoom_factor = 1.0
        
        # Dot tracking - INITIALIZE BEFORE UI CREATION
        self.origin_dot = None
        self.red_dot = None
        self.blue_dot = None
        self.black_dot = None
        self.origin_coords = None
        self.red_dot_coords = None
        self.blue_dot_coords = None
        self.black_dot_coords = None
        self.mouse_x = 0
        self.mouse_y = 0
        
        # Track if mouse is inside image bounds
        self.mouse_inside_image = False
        
        # Drag mode variables
        self.drag_mode = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.image_offset_x = 0
        self.image_offset_y = 0
        
        # Data structures for groups and history
        self.groups = []  # List of group dictionaries
        self.current_group = {
            "name": "",
            "origin": None,
            "red": None,
            "blue": None,
            "black": None,
            "timestamp": None
        }
        self.history_file = "coordinate_groups_history.json"
        
        # Load history on startup
        self.load_history()
        
        # StringVar for coordinate display
        self.coord_var = tk.StringVar(value="Hover over image to see coordinates")
        self.mode_var = tk.StringVar(value="Mode: Coordinate")
        
        # Create main layout with sidebar
        self.create_ui()
        
        # Canvas for image
        self.canvas = tk.Canvas(self.main_frame, bg="gray", cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Bind events
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-1>", self.on_mouse_click)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)  # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)  # Linux scroll down
        self.canvas.bind("<Leave>", self.on_mouse_leave)  # Mouse leaves canvas
        self.root.bind("<Key-1>", self.on_key_1)  # Red
        self.root.bind("<Key-2>", self.on_key_2)  # Blue
        self.root.bind("<Key-3>", self.on_key_3)  # Black
        self.root.bind("<Key-4>", self.on_key_4)  # Origin (green)
        self.root.bind("<Key-z>", self.toggle_drag_mode)
        self.root.bind("<Key-Z>", self.toggle_drag_mode)
        
    def create_ui(self):
        """Create the user interface with sidebar."""
        # Header with instructions
        header_frame = tk.Frame(self.root, bg="#f0f0f0")
        header_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        instructions = tk.Label(
            header_frame,
            text="Open Image | Hover=coords | Click=print | 1=Red | 2=Blue | 3=Black | 4=Origin | Z=Toggle Drag | Scroll=zoom",
            font=("Arial", 10),
            bg="#f0f0f0"
        )
        instructions.pack(pady=5)
        
        # Button frame
        button_frame = tk.Frame(header_frame, bg="#f0f0f0")
        button_frame.pack(pady=5)
        
        open_button = tk.Button(
            button_frame,
            text="Open Image",
            command=self.open_image,
            font=("Arial", 10),
            bg="#4CAF50",
            fg="white",
            padx=10,
            pady=5
        )
        open_button.pack(side=tk.LEFT, padx=5)
        
        # Drag mode toggle button
        self.drag_button = tk.Button(
            button_frame,
            text="🖐️ Drag Mode (Z)",
            command=self.toggle_drag_mode,
            font=("Arial", 10),
            bg="#607D8B",
            fg="white",
            padx=10,
            pady=5
        )
        self.drag_button.pack(side=tk.LEFT, padx=5)
        
        # Mode display
        mode_label = tk.Label(
            button_frame,
            textvariable=self.mode_var,
            font=("Arial", 11, "bold"),
            fg="#FF5722",
            bg="#f0f0f0"
        )
        mode_label.pack(side=tk.LEFT, padx=10)
        
        # Coordinate display
        coord_label = tk.Label(
            button_frame,
            textvariable=self.coord_var,
            font=("Arial", 12, "bold"),
            fg="#2196F3",
            bg="#f0f0f0"
        )
        coord_label.pack(side=tk.LEFT, padx=20)
        
        # Main content area with sidebar
        content_frame = tk.Frame(self.root)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Sidebar for groups and history
        self.sidebar = tk.Frame(content_frame, bg="#e0e0e0", width=350)
        self.sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        self.sidebar.pack_propagate(False)
        
        # Current group section
        group_label = tk.Label(
            self.sidebar,
            text="Current Group",
            font=("Arial", 12, "bold"),
            bg="#e0e0e0"
        )
        group_label.pack(pady=10)
        
        # Group name entry
        name_frame = tk.Frame(self.sidebar, bg="#e0e0e0")
        name_frame.pack(pady=5, padx=10, fill=tk.X)
        
        tk.Label(name_frame, text="Group Name:", bg="#e0e0e0").pack(side=tk.LEFT)
        self.group_name_var = tk.StringVar()
        self.group_name_entry = tk.Entry(name_frame, textvariable=self.group_name_var, width=20)
        self.group_name_entry.pack(side=tk.LEFT, padx=5)
        
        # Bind Enter and Escape keys to the entry widget
        self.group_name_entry.bind("<Return>", self.on_entry_return)
        self.group_name_entry.bind("<Escape>", self.on_entry_escape)
        
        # Bind focus events to track when entry is active
        self.group_name_entry.bind("<FocusIn>", self.on_entry_focus_in)
        self.group_name_entry.bind("<FocusOut>", self.on_entry_focus_out)
        
        # Current coordinates display
        self.current_coords_text = tk.Text(
            self.sidebar,
            height=6,
            width=40,
            font=("Courier", 9),
            bg="#ffffff"
        )
        self.current_coords_text.pack(pady=5, padx=10)
        self.update_current_coords_display()
        
        # Save group button
        save_group_btn = tk.Button(
            self.sidebar,
            text="💾 Save Current Group",
            command=self.save_current_group,
            font=("Arial", 10),
            bg="#2196F3",
            fg="white",
            padx=10,
            pady=5
        )
        save_group_btn.pack(pady=5)
        
        # Clear current button
        clear_btn = tk.Button(
            self.sidebar,
            text="🗑️ Clear Current",
            command=self.clear_current_group,
            font=("Arial", 10),
            bg="#ff9800",
            fg="white",
            padx=10,
            pady=5
        )
        clear_btn.pack(pady=5)
        
        # Separator
        tk.Frame(self.sidebar, height=2, bg="#999").pack(fill=tk.X, pady=10)
        
        # History section
        history_label = tk.Label(
            self.sidebar,
            text="Saved Groups History",
            font=("Arial", 12, "bold"),
            bg="#e0e0e0"
        )
        history_label.pack(pady=5)
        
        # History listbox with scrollbar
        list_frame = tk.Frame(self.sidebar, bg="#e0e0e0")
        list_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.history_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Arial", 9),
            selectmode=tk.SINGLE
        )
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.history_listbox.yview)
        
        self.history_listbox.bind('<<ListboxSelect>>', self.on_history_select)
        
        # History buttons
        history_btn_frame = tk.Frame(self.sidebar, bg="#e0e0e0")
        history_btn_frame.pack(pady=5)
        
        view_btn = tk.Button(
            history_btn_frame,
            text="👁️ View",
            command=self.view_selected_group,
            font=("Arial", 9),
            bg="#4CAF50",
            fg="white",
            padx=8,
            pady=3
        )
        view_btn.pack(side=tk.LEFT, padx=2)
        
        load_btn = tk.Button(
            history_btn_frame,
            text="📥 Load",
            command=self.load_selected_group,
            font=("Arial", 9),
            bg="#2196F3",
            fg="white",
            padx=8,
            pady=3
        )
        load_btn.pack(side=tk.LEFT, padx=2)
        
        delete_btn = tk.Button(
            history_btn_frame,
            text="❌ Delete",
            command=self.delete_selected_group,
            font=("Arial", 9),
            bg="#f44336",
            fg="white",
            padx=8,
            pady=3
        )
        delete_btn.pack(side=tk.LEFT, padx=2)
        
        # Export/Import buttons
        file_btn_frame = tk.Frame(self.sidebar, bg="#e0e0e0")
        file_btn_frame.pack(pady=5)
        
        export_btn = tk.Button(
            file_btn_frame,
            text="📤 Export All",
            command=self.export_groups,
            font=("Arial", 9),
            bg="#9C27B0",
            fg="white",
            padx=8,
            pady=3
        )
        export_btn.pack(side=tk.LEFT, padx=2)
        
        import_btn = tk.Button(
            file_btn_frame,
            text="📥 Import",
            command=self.import_groups,
            font=("Arial", 9),
            bg="#9C27B0",
            fg="white",
            padx=8,
            pady=3
        )
        import_btn.pack(side=tk.LEFT, padx=2)
        
        reset_btn = tk.Button(
            self.sidebar,
            text="🔄 Reset All History",
            command=self.reset_history,
            font=("Arial", 9),
            bg="#f44336",
            fg="white",
            padx=10,
            pady=5
        )
        reset_btn.pack(pady=5)
        
        # Main frame for canvas
        self.main_frame = tk.Frame(content_frame)
        self.main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Update history display
        self.update_history_display()
    
    def on_entry_focus_in(self, event):
        """Called when entry widget gains focus."""
        # Unbind keyboard shortcuts temporarily
        self.root.unbind("<Key-1>")
        self.root.unbind("<Key-2>")
        self.root.unbind("<Key-3>")
        self.root.unbind("<Key-4>")
        self.root.unbind("<Key-z>")
        self.root.unbind("<Key-Z>")
    
    def on_entry_focus_out(self, event):
        """Called when entry widget loses focus."""
        # Rebind keyboard shortcuts
        self.root.bind("<Key-1>", self.on_key_1)
        self.root.bind("<Key-2>", self.on_key_2)
        self.root.bind("<Key-3>", self.on_key_3)
        self.root.bind("<Key-4>", self.on_key_4)
        self.root.bind("<Key-z>", self.toggle_drag_mode)
        self.root.bind("<Key-Z>", self.toggle_drag_mode)
    
    def on_entry_return(self, event):
        """Handle Enter key in entry widget - unfocus."""
        self.canvas.focus_set()
    
    def on_entry_escape(self, event):
        """Handle Escape key in entry widget - unfocus."""
        self.canvas.focus_set()
    
    def toggle_drag_mode(self, event=None):
        """Toggle between coordinate mode and drag mode."""
        self.drag_mode = not self.drag_mode
        
        if self.drag_mode:
            self.canvas.config(cursor="fleur")
            self.mode_var.set("Mode: Drag 🖐️")
            self.drag_button.config(bg="#FF5722", text="✋ Drag Mode (Z)")
        else:
            self.canvas.config(cursor="crosshair")
            self.mode_var.set("Mode: Coordinate ➕")
            self.drag_button.config(bg="#607D8B", text="🖐️ Drag Mode (Z)")
    
    def update_current_coords_display(self):
        """Update the display of current coordinates."""
        self.current_coords_text.delete(1.0, tk.END)
        
        lines = []
        lines.append(f"Origin: {self.format_coord(self.origin_coords)}")
        lines.append(f"Red:    {self.format_coord(self.red_dot_coords)}")
        lines.append(f"Blue:   {self.format_coord(self.blue_dot_coords)}")
        lines.append(f"Black:  {self.format_coord(self.black_dot_coords)}")
        
        self.current_coords_text.insert(1.0, "\n".join(lines))
    
    def format_coord(self, coord):
        """Format coordinate tuple for display."""
        if coord is None:
            return "Not set"
        return f"({coord[0]}, {coord[1]})"
    
    def save_current_group(self):
        """Save the current group to history."""
        if not self.group_name_var.get().strip():
            messagebox.showwarning("No Name", "Please enter a group name.")
            return
        
        if all(c is None for c in [self.origin_coords, self.red_dot_coords, 
                                     self.blue_dot_coords, self.black_dot_coords]):
            messagebox.showwarning("Empty Group", "No coordinates set. Please mark at least one point.")
            return
        
        group = {
            "name": self.group_name_var.get().strip(),
            "origin": self.origin_coords,
            "red": self.red_dot_coords,
            "blue": self.blue_dot_coords,
            "black": self.black_dot_coords,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.groups.append(group)
        self.save_history()
        self.update_history_display()
        
        messagebox.showinfo("Saved", f"Group '{group['name']}' saved successfully!")
        
        # Clear current group name for next entry
        self.group_name_var.set("")
    
    def clear_current_group(self):
        """Clear all current coordinates and dots."""
        # Remove dots from canvas
        if self.origin_dot:
            self.canvas.delete(self.origin_dot)
        if self.red_dot:
            self.canvas.delete(self.red_dot)
        if self.blue_dot:
            self.canvas.delete(self.blue_dot)
        if self.black_dot:
            self.canvas.delete(self.black_dot)
        
        # Reset coordinates
        self.origin_dot = None
        self.red_dot = None
        self.blue_dot = None
        self.black_dot = None
        self.origin_coords = None
        self.red_dot_coords = None
        self.blue_dot_coords = None
        self.black_dot_coords = None
        
        # Clear group name
        self.group_name_var.set("")
        
        # Update display
        self.update_current_coords_display()
    
    def update_history_display(self):
        """Update the history listbox."""
        self.history_listbox.delete(0, tk.END)
        
        for idx, group in enumerate(reversed(self.groups)):
            display_text = f"{group['name']} - {group['timestamp']}"
            self.history_listbox.insert(tk.END, display_text)
    
    def on_history_select(self, event):
        """Handle history item selection."""
        pass  # Selection handled by buttons
    
    def view_selected_group(self):
        """View details of selected group."""
        selection = self.history_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a group to view.")
            return
        
        idx = len(self.groups) - 1 - selection[0]
        group = self.groups[idx]
        
        details = f"Group: {group['name']}\n"
        details += f"Saved: {group['timestamp']}\n\n"
        details += f"Origin: {self.format_coord(group['origin'])}\n"
        details += f"Red:    {self.format_coord(group['red'])}\n"
        details += f"Blue:   {self.format_coord(group['blue'])}\n"
        details += f"Black:  {self.format_coord(group['black'])}"
        
        messagebox.showinfo("Group Details", details)
    
    def load_selected_group(self):
        """Load selected group into current coordinates."""
        selection = self.history_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a group to load.")
            return
        
        idx = len(self.groups) - 1 - selection[0]
        group = self.groups[idx]
        
        # Clear current
        self.clear_current_group()
        
        # Load coordinates
        self.group_name_var.set(group['name'] + " (copy)")
        self.origin_coords = group['origin']
        self.red_dot_coords = group['red']
        self.blue_dot_coords = group['blue']
        self.black_dot_coords = group['black']
        
        # Update display
        self.update_current_coords_display()
        
        # Redraw dots if image is loaded
        if self.image is not None:
            self.redraw_all_dots()
        
        messagebox.showinfo("Loaded", f"Group '{group['name']}' loaded into current coordinates.")
    
    def delete_selected_group(self):
        """Delete selected group from history."""
        selection = self.history_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a group to delete.")
            return
        
        idx = len(self.groups) - 1 - selection[0]
        group = self.groups[idx]
        
        if messagebox.askyesno("Confirm Delete", f"Delete group '{group['name']}'?"):
            self.groups.pop(idx)
            self.save_history()
            self.update_history_display()
    
    def export_groups(self):
        """Export all groups to a JSON file."""
        if not self.groups:
            messagebox.showwarning("No Data", "No groups to export.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Groups",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="coordinate_groups_export.json"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(self.groups, f, indent=2)
                messagebox.showinfo("Success", f"Exported {len(self.groups)} groups to {file_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {str(e)}")
    
    def import_groups(self):
        """Import groups from a JSON file."""
        file_path = filedialog.askopenfilename(
            title="Import Groups",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    imported_groups = json.load(f)
                
                # Validate structure
                if not isinstance(imported_groups, list):
                    raise ValueError("Invalid file format")
                
                # Add imported groups
                self.groups.extend(imported_groups)
                self.save_history()
                self.update_history_display()
                
                messagebox.showinfo("Success", f"Imported {len(imported_groups)} groups.")
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import: {str(e)}")
    
    def reset_history(self):
        """Reset all history."""
        if messagebox.askyesno("Confirm Reset", "Delete ALL saved groups? This cannot be undone!"):
            self.groups = []
            self.save_history()
            self.update_history_display()
            messagebox.showinfo("Reset", "All history has been cleared.")
    
    def load_history(self):
        """Load groups from history file."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    self.groups = json.load(f)
            except Exception as e:
                print(f"Error loading history: {e}")
                self.groups = []
    
    def save_history(self):
        """Save groups to history file."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.groups, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")
    
    def open_image(self):
        """Open an image file dialog and load the image."""
        file_path = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.tiff"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            try:
                self.original_image = Image.open(file_path)
                self.image = self.original_image.copy()
                self.display_image()
                self.root.title(f"Florence Nightingale's Rose Diagram - {os.path.basename(file_path)}")
                
                # Redraw any existing dots
                self.redraw_all_dots()
            except Exception as e:
                self.coord_var.set(f"Error loading image: {str(e)}")
    
    def display_image(self):
        """Display the image on the canvas."""
        if self.image is None:
            return
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 1:
            canvas_width = 800
        if canvas_height <= 1:
            canvas_height = 500
        
        orig_width, orig_height = self.original_image.size
        
        self.image = self.original_image.copy()
        display_width = int((canvas_width - 20) * self.zoom_factor)
        display_height = int((canvas_height - 20) * self.zoom_factor)
        self.image.thumbnail((display_width, display_height), Image.Resampling.LANCZOS)
        
        self.scale_x = orig_width / self.image.width
        self.scale_y = orig_height / self.image.height
        
        self.photo_image = ImageTk.PhotoImage(self.image)
        
        self.canvas.delete("all")
        
        x = (canvas_width - self.photo_image.width()) // 2
        y = (canvas_height - self.photo_image.height()) // 2
        
        self.canvas_image = self.canvas.create_image(
            x, y,
            image=self.photo_image,
            anchor="nw"
        )
        
        self.image_offset_x = x
        self.image_offset_y = y
        
        zoom_percent = int(self.zoom_factor * 100)
        self.coord_var.set(f"Image loaded ({orig_width}x{orig_height}) - Zoom: {zoom_percent}%")
    
    def on_mouse_leave(self, event):
        """Handle mouse leaving the canvas."""
        self.mouse_inside_image = False
        if not self.drag_mode:
            self.coord_var.set("Outside image bounds")
    
    def on_mouse_move(self, event):
        """Handle mouse motion to display coordinates."""
        if self.image is None or self.original_image is None:
            return
        
        self.mouse_x = event.x
        self.mouse_y = event.y
        
        pixel_x = event.x - self.image_offset_x
        pixel_y = event.y - self.image_offset_y
        
        if (0 <= pixel_x < self.photo_image.width() and 
            0 <= pixel_y < self.photo_image.height()):
            self.mouse_inside_image = True
            orig_x = int(pixel_x * self.scale_x)
            orig_y = int(pixel_y * self.scale_y)
            if not self.drag_mode:
                self.coord_var.set(f"X: {orig_x}  Y: {orig_y}")
        else:
            self.mouse_inside_image = False
            if not self.drag_mode:
                self.coord_var.set("Outside image bounds")
    
    def on_mouse_click(self, event):
        """Handle mouse click to print coordinates or start dragging."""
        if self.drag_mode:
            # Start drag
            self.drag_start_x = event.x
            self.drag_start_y = event.y
            return
        
        if self.image is None or self.original_image is None:
            print("No image loaded")
            return
        
        pixel_x = event.x - self.image_offset_x
        pixel_y = event.y - self.image_offset_y
        
        if (0 <= pixel_x < self.photo_image.width() and 
            0 <= pixel_y < self.photo_image.height()):
            orig_x = int(pixel_x * self.scale_x)
            orig_y = int(pixel_y * self.scale_y)
            print(f"Clicked at: X={orig_x}, Y={orig_y}")
        else:
            print("Click outside image bounds")
    
    def on_mouse_drag(self, event):
        """Handle mouse drag to move the image."""
        if not self.drag_mode or self.image is None:
            return
        
        # Calculate drag offset
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        
        # Update image position
        self.image_offset_x += dx
        self.image_offset_y += dy
        
        # Redraw image at new position
        self.canvas.coords(self.canvas_image, self.image_offset_x, self.image_offset_y)
        
        # Delete old dots before redrawing
        if self.origin_dot:
            self.canvas.delete(self.origin_dot)
            self.origin_dot = None
        if self.red_dot:
            self.canvas.delete(self.red_dot)
            self.red_dot = None
        if self.blue_dot:
            self.canvas.delete(self.blue_dot)
            self.blue_dot = None
        if self.black_dot:
            self.canvas.delete(self.black_dot)
            self.black_dot = None
        
        # Redraw dots at new positions
        self.redraw_all_dots()
        
        # Update drag start position
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
        self.coord_var.set("Dragging image...")
    
    def on_mouse_release(self, event):
        """Handle mouse button release."""
        if self.drag_mode:
            self.coord_var.set("Drag mode active")
    
    def place_dot(self, color):
        """Place a colored dot at the current mouse position."""
        if self.image is None or self.original_image is None:
            return
        
        if self.drag_mode:
            return  # Don't place dots in drag mode
        
        # Check if mouse is inside image bounds
        if not self.mouse_inside_image:
            return  # Don't place dots outside image
        
        pixel_x = self.mouse_x - self.image_offset_x
        pixel_y = self.mouse_y - self.image_offset_y
        
        if (0 <= pixel_x < self.photo_image.width() and 
            0 <= pixel_y < self.photo_image.height()):
            orig_x = int(pixel_x * self.scale_x)
            orig_y = int(pixel_y * self.scale_y)
            
            # Remove existing dot
            if color == "green":  # Origin
                if self.origin_dot is not None:
                    self.canvas.delete(self.origin_dot)
            elif color == "red":
                if self.red_dot is not None:
                    self.canvas.delete(self.red_dot)
            elif color == "blue":
                if self.blue_dot is not None:
                    self.canvas.delete(self.blue_dot)
            elif color == "black":
                if self.black_dot is not None:
                    self.canvas.delete(self.black_dot)
            
            # Draw new dot
            dot_radius = 4
            x1 = self.mouse_x - dot_radius
            y1 = self.mouse_y - dot_radius
            x2 = self.mouse_x + dot_radius
            y2 = self.mouse_y + dot_radius
            
            new_dot = self.canvas.create_oval(
                x1, y1, x2, y2,
                fill=color,
                outline="white",
                width=2
            )
            
            # Store the dot
            if color == "green":  # Origin
                self.origin_dot = new_dot
                self.origin_coords = (orig_x, orig_y)
                print(f"Origin ({orig_x}, {orig_y})")
            elif color == "red":
                self.red_dot = new_dot
                self.red_dot_coords = (orig_x, orig_y)
                print(f"Red dot ({orig_x}, {orig_y})")
            elif color == "blue":
                self.blue_dot = new_dot
                self.blue_dot_coords = (orig_x, orig_y)
                print(f"Blue dot ({orig_x}, {orig_y})")
            elif color == "black":
                self.black_dot = new_dot
                self.black_dot_coords = (orig_x, orig_y)
                print(f"Black dot ({orig_x}, {orig_y})")
            
            # Update display
            self.update_current_coords_display()
    
    def on_key_1(self, event):
        """Handle key 1 - place red dot."""
        self.place_dot("red")
    
    def on_key_2(self, event):
        """Handle key 2 - place blue dot."""
        self.place_dot("blue")
    
    def on_key_3(self, event):
        """Handle key 3 - place black dot."""
        self.place_dot("black")
    
    def on_key_4(self, event):
        """Handle key 4 - place origin (green) dot."""
        self.place_dot("green")
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel to zoom in/out."""
        if self.image is None or self.original_image is None:
            return
        
        if event.num == 5 or event.delta < 0:
            self.zoom_factor *= 0.9
        elif event.num == 4 or event.delta > 0:
            self.zoom_factor *= 1.1
        
        self.zoom_factor = max(0.1, min(3.0, self.zoom_factor))
        
        self.display_image()
        self.redraw_all_dots()
    
    def redraw_all_dots(self):
        """Redraw all dots after zoom or image change."""
        def redraw_dot_at_coords(color, coords, dot_attr_name):
            if coords is None:
                return
            orig_x, orig_y = coords
            display_x = int(orig_x / self.scale_x) + self.image_offset_x
            display_y = int(orig_y / self.scale_y) + self.image_offset_y
            
            dot_radius = 4
            x1 = display_x - dot_radius
            y1 = display_y - dot_radius
            x2 = display_x + dot_radius
            y2 = display_y + dot_radius
            
            new_dot = self.canvas.create_oval(
                x1, y1, x2, y2,
                fill=color,
                outline="white",
                width=2
            )
            
            setattr(self, dot_attr_name, new_dot)
        
        redraw_dot_at_coords("green", self.origin_coords, "origin_dot")
        redraw_dot_at_coords("red", self.red_dot_coords, "red_dot")
        redraw_dot_at_coords("blue", self.blue_dot_coords, "blue_dot")
        redraw_dot_at_coords("black", self.black_dot_coords, "black_dot")


def main():
    root = tk.Tk()
    app = ImageXYReader(root)
    root.mainloop()


if __name__ == "__main__":
    main()