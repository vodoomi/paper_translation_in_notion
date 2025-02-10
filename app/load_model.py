from pix2text import Pix2Text

if __name__ == '__main__':
    # Load the model
    model = Pix2Text().from_config(enable_table=False)