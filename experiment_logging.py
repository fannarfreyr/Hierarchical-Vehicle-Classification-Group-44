import datetime
import traceback
import os
import matplotlib.pyplot as plt
import numpy as np

class ExperimentLogger:

    def __init__(self, log_file="experiment_log.md", active=True, show_console=True):
        self.log_file = log_file
        self.active = active
        self.show_console = show_console

        # Internal storage
        self.reset()

        if self.active:
            os.makedirs(os.path.dirname(log_file), exist_ok=True) if "/" in log_file else None

    def reset(self):
        """Reset stored experiment info."""
        self.name = None
        self.changes = None
        self.reason = None
        self.metrics = []
        self.results = None
        self.notes = None
        self.error = None
        self.extra_images = []

    # ----------------------------
    # BASIC EXPERIMENT INFO
    # ----------------------------
    def set(self, name, changes=None, reason=None):
        if not self.active:
            return

        self.name = name
        self.changes = changes
        self.reason = reason

    # ----------------------------
    # METRIC LOGGING
    # ----------------------------
    def record_metrics(self, epoch, **kwargs):
        if not self.active:
            return

        metric_line = {"epoch": epoch}
        metric_line.update(kwargs)
        self.metrics.append(metric_line)

    # ----------------------------
    # PLOT & IMAGE SUPPORT
    # ----------------------------
    def add_image(self, image, name="image"):
    
        if not self.active:
            return
    
        os.makedirs("plots", exist_ok=True)
    
        # Convert PyTorch tensor to NumPy
        if "torch" in str(type(image)):
            image = image.detach().cpu().numpy()
    
        # If CHW → HWC
        if len(image.shape) == 3 and image.shape[0] in [1,3]:
            image = np.transpose(image, (1, 2, 0))
    
        # If single channel, squeeze last dim
        if image.shape[-1] == 1:
            image = image.squeeze(-1)
    
        # Unnormalize if RGB (assuming ImageNet)
        if len(image.shape) == 3 and image.shape[2] == 3:
            mean = np.array([0.485, 0.456, 0.406])
            std  = np.array([0.229, 0.224, 0.225])
            image = (image * std) + mean
    
        # Clip to [0,1] and convert to float32
        image = np.clip(image, 0, 1).astype(np.float32)
    
        filename = f"plots/{self.name}_{name}.png"
        plt.imsave(filename, image)
        self.extra_images.append(filename)



    def add_confusion_matrix(self, cm, class_names, name="confusion_matrix"):
        if not self.active:
            return

        fig, ax = plt.subplots(figsize=(6, 6))
        im = ax.imshow(cm, cmap="Blues")
        fig.colorbar(im)

        ax.set_xticks(np.arange(len(class_names)))
        ax.set_yticks(np.arange(len(class_names)))
        ax.set_xticklabels(class_names)
        ax.set_yticklabels(class_names)
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

        for i in range(len(class_names)):
            for j in range(len(class_names)):
                ax.text(j, i, f"{cm[i, j]}", ha="center", va="center")

        ax.set_xlabel("Predicted")
        ax.set_ylabel("True")
        ax.set_title("Confusion Matrix")

        self.add_plot(fig, name)

    def add_image(self, image, name="image"):
        if not self.active:
            return

        os.makedirs("plots", exist_ok=True)

        # Convert PyTorch tensor → NumPy
        if "torch" in str(type(image)):
            image = image.detach().cpu().numpy()

        # CHW → HWC
        if len(image.shape) == 3:
            image = np.transpose(image, (1, 2, 0))

        filename = f"plots/{self.name}_{name}.png"
        plt.imsave(filename, image)
        self.extra_images.append(filename)

    # ----------------------------
    # ERROR CAPTURE
    # ----------------------------
    def capture_errors(self, fn, *args, **kwargs):
        if not self.active:
            return fn(*args, **kwargs)

        try:
            return fn(*args, **kwargs)
        except Exception as e:
            self.error = traceback.format_exc()
            return None

    # ----------------------------
    # COMMIT TO MARKDOWN FILE
    # ----------------------------
    def commit(self):
        if not self.active:
            print(" Logger inactive — nothing saved.")
            return

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"## Experiment: {self.name}\n"
        entry += f"**Date:** {timestamp}\n\n"

        if self.changes:
            entry += f"### Changes\n{self.changes}\n\n"
        if self.reason:
            entry += f"### Reason\n{self.reason}\n\n"

        if self.metrics:
            entry += "### Epoch Metrics\n"
            for m in self.metrics:
                metrics_text = ", ".join([f"{k}={v:.4f}" if isinstance(v, (float, int)) else f"{k}={v}" 
                                          for k, v in m.items() if k != "epoch"])
                entry += f"- Epoch {m['epoch']}: {metrics_text}\n"
            entry += "\n"

        if self.results:
            entry += f"### Final Results\n{self.results}\n\n"

        if self.notes:
            entry += f"### Notes\n{self.notes}\n\n"

        if self.error:
            entry += f"### Errors\n```\n{self.error}\n```\n\n"

        # Embed saved images/plots
        if self.extra_images:
            entry += "### Plots and Images\n"
            for img in self.extra_images:
                entry += f"![Plot]({img})\n\n"

        entry += "---\n\n"

        # Write to log file
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(entry)

        if self.show_console:
            print(f"📄 Logged experiment '{self.name}' → {self.log_file}")

        self.reset()
