import bachelor_thesis.dataset
import gensim.models
import h5py
import os.path
import progressbar
import skeltorch
import string
import torch
import torch.utils.data
import torchtext.data.utils


class BachelorThesisData(skeltorch.Data):
    words_list = None
    words_embeddings = None

    def create(self, data_path):
        """Creates the dictionary along with its word embeddings.

        Stores as a class attribute a ``torch.Tensor`` of size (dict_size, embedding_size) with the Word2Vec embeddings
        used in a ``torch.nn.Embedding`` layer. Only the first ``dict_size`` words (ordered by frequency) are stored.

        Args:
            data_path (str): ``--data-path`` command argument.
        """
        self.logger.info('Creating dictionary...')
        data = self._get_data(data_path)
        words_dict = {}
        tokenizer = torchtext.data.utils.get_tokenizer('basic_english')
        bar = progressbar.ProgressBar(max_value=len(data['news/reuters'].keys()))
        for i, day in enumerate(data['news/reuters'].keys()):
            day_news = data['news/reuters'][day][()]
            for new_index in range(day_news.shape[0]):
                for new_word in tokenizer(day_news[new_index, 0].translate(str.maketrans('', '', string.punctuation))):
                    words_dict[new_word] = words_dict[new_word] + 1 if new_word in words_dict else 1
            bar.update(i)
        self._create_words_embeddings(data_path, words_dict)

    def _create_words_embeddings(self, data_path, words_dict):
        dict_size = self.experiment.configuration.get('data', 'dict_size')
        self.words_list = ['<EMP>', '<UNK>']
        self.words_embeddings = [torch.zeros((300,)), torch.ones((300,))]
        word2vec = gensim.models.KeyedVectors.load_word2vec_format(os.path.join(data_path, 'word2vec.bin'), binary=True)
        for word in sorted(words_dict.keys(), key=lambda x: words_dict[x], reverse=True):
            if word in word2vec:
                self.words_list.append(word)
                self.words_embeddings.append(torch.from_numpy(word2vec[word]))
            if len(self.words_list) >= dict_size:
                break
        self.words_embeddings = torch.stack(self.words_embeddings)

    def load_datasets(self, data_path):
        data = self._get_data(data_path)
        symbol = self.experiment.configuration.get('data', 'symbol')
        train_years = self.experiment.configuration.get('data', 'train_years')
        validation_years = self.experiment.configuration.get('data', 'validation_years')
        test_years = self.experiment.configuration.get('data', 'test_years')
        n_news = self.experiment.configuration.get('data', 'n_news')
        n_words = self.experiment.configuration.get('data', 'n_words')
        self.datasets['train'] = bachelor_thesis.dataset.BachelorThesisDataset(
            data, symbol, train_years, self.words_list, n_news, n_words
        )
        self.datasets['validation'] = bachelor_thesis.dataset.BachelorThesisDataset(
            data, symbol, validation_years, self.words_list, n_news, n_words
        )
        self.datasets['test'] = bachelor_thesis.dataset.BachelorThesisDataset(
            data, symbol, test_years, self.words_list, n_news, n_words
        )

    def _get_data(self, data_path):
        return h5py.File(os.path.join(data_path, 'bachelor_thesis_data.hdf5'), "r")

    def load_loaders(self, data_path, num_workers):
        self.loaders['train'] = torch.utils.data.DataLoader(
            dataset=self.datasets['train'],
            batch_size=self.experiment.configuration.get('training', 'batch_size'),
            num_workers=num_workers,
            shuffle=True
        )
        self.loaders['validation'] = torch.utils.data.DataLoader(
            dataset=self.datasets['validation'],
            batch_size=self.experiment.configuration.get('training', 'batch_size'),
            num_workers=num_workers,
            shuffle=True
        )
        self.loaders['test'] = torch.utils.data.DataLoader(
            dataset=self.datasets['test'],
            batch_size=self.experiment.configuration.get('training', 'batch_size'),
            num_workers=num_workers,
            shuffle=True
        )

