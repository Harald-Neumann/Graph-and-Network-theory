from pathlib import Path
from tempfile import TemporaryDirectory
import matplotlib as mpl
from matplotlib.animation import cbook, writers, PillowWriter, HTMLWriter, FileMovieWriter
import warnings
import inspect


class ExtendedAnimation():
    """At the moment only JS recording / playback is supported
    """

    def __init__(self, fig=None, func=None, interval=200):
        self._isRunning = False
        if fig is None:
            self._fig = mpl.figure.Figure()
        else:
            self._fig = fig
        self._func = func
        self._repeat = False
        self._record = None
        self._filename_field = None
        self._writer = None
        self._interval = interval

    @property
    def _filename(self):
        if self._filename_field is None:
            self._tmp_cx = TemporaryDirectory()
            self._filename_field = Path(self._tmp_cx.__enter__()) / "temp.html"
        return self._filename_field

    @_filename.setter
    def _filename(self, value):
        if hasattr(self, "_tmp_cx"):
            self._tmp_cx.__exit__(None, None, None)
            del self._tmp_cx
        self._filename_field = value

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    def __del__(self):
        if not getattr(self, '_draw_was_started', False):
            warnings.warn(
                'Animation was deleted without rendering anything. This is '
                'most likely not intended. To prevent deletion, assign the '
                'Animation to a variable, e.g. `anim`, that exists until you '
                'have outputted the Animation using `plt.show()` or '
                '`anim.save()`.')

    def save(self, rerun=False, *args, **kwargs):
        if not self._record or rerun:
            if hasattr(self._func, "__call__"):
                self.start()
                if inspect.isgeneratorfunction(self._func):
                    for _ in self._func(*args, **kwargs):
                        self.save_frame()
                else:
                    self._func(self, *args, **kwargs)
                self.stop()
            else:
                raise RuntimeError("Saves require a function to be provided")
        elif self._record:
            pass
        else:
            raise RuntimeError("No Function or Record provided")

    def start(self):
        self._savefig_kwargs = {}
        dpi = mpl.rcParams['savefig.dpi']
        if dpi == 'figure':
            dpi = self._fig.dpi
        writer_kwargs = {}
        self._writer = HTMLWriter(
            fps=1000. / self._interval, embed_frames=True, default_mode="loop")
        self._context = [mpl.rc_context({"savefig.bbox": None}),
                         self._writer.saving(self._fig, self._filename, dpi),
                         cbook._setattr_cm(self._fig.canvas, _is_saving=True, manager=None)]
        for ctx in self._context:
            ctx.__enter__()
        self._init_draw()

    def _init_draw(self):
        self._isRunning = True

    def save_frame(self):
        if not self._isRunning:
            raise RuntimeError(
                "You must first call `start()` to begin saving frames")
        self._writer.grab_frame(**self._savefig_kwargs)

    def stop(self):
        if not self._isRunning:
            raise RuntimeError(
                "You must first call `start()` to begin saving frames")
        for ctx in reversed(self._context):
            ctx.__exit__(None, None, None)
        self._record = Path(self._filename).read_text()

    def to_jshtml(self, fps=None, embed_frames=True, default_mode=None):
        if self._isRunning:
            self.stop()
        if self._record is None:
            self.save()
        return self._record

    def _repr_html_(self):
        """IPython display hook for rendering."""
        fmt = mpl.rcParams['animation.html']
        if fmt == 'html5':
            raise NotImplementedError(
                "IPython display for HTML5 is not implemented")
            # return self.to_html5_video()
        elif fmt == 'jshtml':
            return self.to_jshtml()
