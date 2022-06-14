import base64
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import matplotlib as mpl
from matplotlib.animation import cbook, HTMLWriter
import warnings
from typing import Any
from matplotlib.animation import writers
import inspect

        
VIDEO_TAG = r'''<video {size} {options}>
  <source type="video/mp4" src="data:video/mp4;base64,{video}">
  Your browser does not support the video tag.
</video>'''


class ExtendedAnimation():
    """At the moment only JS recording / playback is supported
    """

    def __init__(self, fig=None, func=None, interval=200):
        if fig is None:
            self._fig = mpl.figure.Figure()
        else:
            self._fig = fig
        self._interval = interval
        self._storage = []
        self._savefig_kwargs = {}
        self._has_changed = [False] * 2
        self._context = [mpl.rc_context({"savefig.bbox": None}),
                         cbook._setattr_cm(self._fig.canvas, _is_saving=True, manager=None)]
        self._func = func
        for ctx in self._context:
            ctx.__enter__()

    def __del__(self):
        for ctx in reversed(self._context):
            ctx.__exit__(None, None, None)

    def save_frame(self):
        i = BytesIO()
        self._fig.savefig(i, format="png", **self._savefig_kwargs)
        self._storage.append(i)
        self._has_changed = [True] * 2


    def to_jshtml(self, fps=None, embed_frames=True, default_mode="loop"):
        if not self._storage and self._func:
            if inspect.isgeneratorfunction(self._func):
                for _ in self._func():
                    self.save_frame()
            else:
                self._func(self)
        if self._has_changed[0]:
            if embed_frames:
                with TemporaryDirectory() as tmpdir:
                    path = Path(tmpdir) / "temp.html"
                    writer = HTMLWriter(fps=1000./self._interval, embed_frames=embed_frames, default_mode=default_mode)
                    with writer.saving(self._fig, path, self._fig.dpi):
                        for frame in self._storage:
                            imgdata64 = base64.encodebytes(frame.getvalue()).decode("ascii")
                            writer._saved_frames.append(imgdata64)
                    self._html_representation = path.read_text()
                    self._has_changed[0] = False
            else:
                raise NotImplementedError("No support for non-embedded frames yet")

        return self._html_representation

    def to_html5_video(self, embed_limit=None):
        if self._has_changed[1]:
            with TemporaryDirectory() as tmpdir:
                path = Path(tmpdir) / "temp.m4v"
                Writer = writers[mpl.rcParams['animation.writer']]
                writer = Writer(codec="h264",
                    bitrate=mpl.rcParams['animation.bitrate'], fps=1000./self._interval)
                # TODO: This is not working yet
                vid64 = base64.encodebytes(path.read_bytes())
            vid_len = len(vid64)
            embed_limit = embed_limit or mpl.rcParams['animation.embed_limit']
            if vid_len >= embed_limit:
                warnings.warn("Animation is too large to embed in HTML")
            else:
                self._base64_video = vid64.decode("ascii")
                self._video_size = f'width="{self._fig.canvas.get_width_height()[0]}" height="{self._fig.canvas.get_width_height()[1]}"'
            
            self._has_changed[1]

        if hasattr(self, "_base64_video"):
            return VIDEO_TAG.format(video=self._base64_video,
                                    size=self._video_size,
                                    options="controls autoplay loop")                

    def _repr_html_(self):
        """IPython display hook for rendering."""
        fmt = mpl.rcParams['animation.html']
        if fmt == 'html5':
            raise NotImplementedError(
                "IPython display for HTML5 is not implemented")
            # return self.to_html5_video()
        elif fmt == 'jshtml':
            return self.to_jshtml()

