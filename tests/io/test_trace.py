
from recipes.io.trace import TracePrints, TraceWarnings

if __name__ == '__main__':
    sys.stdout = TracePrints()
    print('Hello World!')
    # restore
    sys.stdout = sys.stdout.stdout

    wtb = TraceWarnings()
    warnings.warn('Dinosaurs!!')
    # restore
    wtb.off()
