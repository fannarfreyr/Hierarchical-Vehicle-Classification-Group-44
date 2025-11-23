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

        self.reset()

        if self.active and "/" in log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # ----------------------------------------------------
    # RESET
    # ----------------------------------------------------
    def reset(self):
        self.name = None
        self.changes = None
        self.reason = None
        self.metrics = []
        self.results = None
        self.notes = None
        self.error = None
        self.extra_images = []

        # NEW — storage for top-1 and top-5 accuracy
        self.top1 = []
        self.top5 = []

    # ----------------------------------------------------
    # BASIC INFO
    # ----------------------------------------------------
    def set(self, name, changes=None, reason=None):
        if not self.active:
            return
        self.name = name
        self.changes = changes
        self.reason = reason

    # ----------------------------------------------------
    # SCALAR METRICS (TensorBoard-style)
    # ----------------------------------------------------
    def add_scalar(self, name, value, epoch=None):
        if not self.active:
            return

        entry = {"metric": name, "value": float(value)}
        if epoch is not None:
            entry["epoch"] = epoch

        self.metrics.append(entry)

        if self.show_console:
            print(f"[Scalar] {name}: {value}")

    # ----------------------------------------------------
    # EPOCH METRICS (grouped)
    # ----------------------------------------------------
    def record_metrics(self, epoch, **kwargs):
        if not self.active:
            return

        entry = {"epoch": epoch}

        # --- NEW: detect top1/top5 automatically
        for key, value in kwargs.items():
            key_lower = key.lower()

            if "top1" in key_lower or "top_1" in key_lower:
                self.top1.append(float(value))

            elif "top5" in key_lower or "top_5" in key_lower:
                self.top5.append(float(value))

            entry[key] = value

        self.metrics.append(entry)

    # ----------------------------------------------------
    # ADD PLOT
    # ----------------------------------------------------
    def add_plot(self, fig, name="plot"):
        if not self.active:
            return

        os.makedirs("plots", exist_ok=True)
        filename = f"plots/{self.name}_{name}.png"
        fig.savefig(filename)
        plt.close(fig)
        self.extra_images.append(filename)

        if self.show_console:
            print(f"[Plot Saved] {filename}")

    # ----------------------------------------------------
    # ADD IMAGE (with un-normalization)
    # ----------------------------------------------------
    def add_image(self, image, name="image"):
        if not self.active:
            return

        os.makedirs("plots", exist_ok=True)

        # Tensor → NumPy
        if "torch" in str(type(image)):
            image = image.detach().cpu().numpy()

        # CHW → HWC
        if len(image.shape) == 3 and image.shape[0] in [1, 3]:
            image = np.transpose(image, (1, 2, 0))

        # Grayscale squeeze
        if image.ndim == 3 and image.shape[-1] == 1:
            image = image.squeeze(-1)

        # Unnormalize if RGB
        if len(image.shape) == 3 and image.shape[2] == 3:
            mean = np.array([0.485, 0.456, 0.406])
            std = np.array([0.229, 0.224, 0.225])
            image = (image * std) + mean

        image = np.clip(image, 0, 1).astype(np.float32)

        timestamp = datetime.datetime.now().strftime("%m_%d_%H_%M")
        filename = f"plots/{self.name}_{timestamp}_{name}.png"
        plt.imsave(filename, image)
        self.extra_images.append(filename)

        if self.show_console:
            print(f"[Image Saved] {filename}")

    # ----------------------------------------------------
    # CONFUSION MATRIX
    # ----------------------------------------------------
    def add_confusion_matrix(self, cm, class_names, name="confusion_matrix"):
        fig, ax = plt.subplots(figsize=(18, 18))
        im = ax.imshow(cm, cmap="Blues")

        fig.colorbar(im)

        n = len(class_names)
        step = max(1, n // 25)

        ax.set_xticks(np.arange(0, n, step))
        ax.set_yticks(np.arange(0, n, step))

        ax.set_xticklabels([class_names[i] for i in range(0, n, step)],
                           rotation=90, fontsize=5)
        ax.set_yticklabels([class_names[i] for i in range(0, n, step)],
                           fontsize=5)

        ax.set_xlabel("Predicted")
        ax.set_ylabel("True")
        ax.set_title("Confusion Matrix")

        plt.tight_layout()

        timestamp = datetime.datetime.now().strftime("%m_%d_%H_%M")
        filename = f"plots/{self.name}_{timestamp}_{name}.png"
        fig.savefig(filename, dpi=300)
        plt.close(fig)
        self.extra_images.append(filename)

    # ----------------------------------------------------
    # ERROR CAPTURE
    # ----------------------------------------------------
    def capture_errors(self, fn, *args, **kwargs):
        if not self.active:
            return fn(*args, **kwargs)
        try:
            return fn(*args, **kwargs)
        except Exception:
            self.error = traceback.format_exc()
            return None

    # ----------------------------------------------------
    # COMMIT TO MARKDOWN
    # ----------------------------------------------------
    def commit(self):
        if not self.active:
            print("Logger inactive — nothing saved.")
            return

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        entry = f"## Experiment: {self.name}\n"
        entry += f"**Date:** {timestamp}\n\n"

        if self.changes:
            entry += f"### Changes\n{self.changes}\n\n"
        if self.reason:
            entry += f"### Reason\n{self.reason}\n\n"

        # Metrics block
        if self.metrics:
            entry += "### Metrics\n"
            for m in self.metrics:
                if "epoch" in m:
                    epoch = m["epoch"]
                    kv = ", ".join(f"{k}={v}" for k, v in m.items() if k != "epoch")
                    entry += f"- Epoch {epoch}: {kv}\n"
                else:
                    entry += f"- {m['metric']}: {m['value']}\n"
            entry += "\n"

        # NEW — Top-1 and Top-5 sections
        if self.top1:
            entry += "### Top-1 Accuracy per Epoch\n"
            entry += f"{self.top1}\n\n"

        if self.top5:
            entry += "### Top-5 Accuracy per Epoch\n"
            entry += f"{self.top5}\n\n"

        if self.results:
            entry += f"### Results\n{self.results}\n\n"

        if self.notes:
            entry += f"### Notes\n{self.notes}\n\n"

        if self.error:
            entry += f"### Errors\n```\n{self.error}\n```\n\n"

        if self.extra_images:
            entry += "### Images / Plots\n"
            for img in self.extra_images:
                entry += f"![img]({img})\n"

        entry += "\n---\n\n"

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(entry)

        if self.show_console:
            print(f"Logged experiment '{self.name}' → {self.log_file}")

        self.reset()
