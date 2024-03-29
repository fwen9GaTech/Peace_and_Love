import os
from datetime import datetime
from time import time

import torch
from torch.utils.tensorboard import SummaryWriter

from deephumor.experiments.metrics import perplexity


class Trainer:
    """An ultimate class for running the models."""
    def __init__(self, experiment_title, log_dir='./logs', text_labels=False,
                 phases=('train', 'val'), clip_norm=3., log_grad_norm=False,
                 unk_index=0, pad_index=0, device='cuda'):
        self.experiment_data = self._setup_experiment(experiment_title, log_dir)

        self.text_labels = text_labels
        self.phases = phases
        self.clip_norm = clip_norm
        self.log_grad_norm = log_grad_norm

        self.unk_index = unk_index
        self.pad_index = pad_index
        self.device = device

        self.writers = self._setup_writers()

    @staticmethod
    def _setup_experiment(title, log_dir='./logs'):
        # experiment_name = "{}_{}".format(title, datetime.now().strftime("%d.%m.%Y-%H:%M:%S"))
        experiment_name = "{}_{}".format(title, datetime.now().strftime("%H-%M-%S"))
        experiment_dir = os.path.join(log_dir, experiment_name)
        best_model_path = f"{title}.best.pth"

        experiment_data = {
            'model_name': title,
            'name': experiment_name,
            'dir': experiment_dir,
            'best_model_path': best_model_path,
            'epochs': 0,
            'iterations': 0,
        }

        return experiment_data

    def _setup_writers(self):
        return {
            phase: SummaryWriter(log_dir=os.path.join(self.experiment_data['dir'], phase))
            for phase in self.phases
        }

    def run_epoch(self, model, dataloader, optimizer, criterion, phase='train'):
        is_train = (phase == 'train')
        model.train() if is_train else model.eval()

        epoch = self.experiment_data['epochs']
        iterations = self.experiment_data['iterations']
        epoch_loss, epoch_pp = 0., 0.

        with torch.set_grad_enabled(is_train):
            for batch in dataloader:
                # unpack batch
                labels, captions, images = batch
                bs, max_len = captions.size()

                captions, images = captions.to(self.device), images.to(self.device)
                lengths = captions.size(1) - (captions == self.pad_index).sum(dim=1)

                if self.text_labels:
                    labels = labels.to(self.device)
                    pred = model(images, captions[:, :-1], lengths, labels)
                else:
                    pred = model(images, captions[:, :-1], lengths)

                pred = pred[:, :max_len, :]

                mask = captions != self.pad_index
                loss = criterion(pred[mask], captions[mask])

                with torch.no_grad():
                    pp = perplexity(pred, captions, lengths, self.pad_index)

                if self.writers is not None and phase in self.writers and is_train:
                    # make optimization step
                    optimizer.zero_grad()
                    loss.backward()

                    if self.log_grad_norm:
                        self.writers[phase].add_scalar(f"train/grad_norm", gradient_norm(model).item(), iterations)
                        torch.nn.utils.clip_grad_norm_(model.parameters(), self.clip_norm)

                    optimizer.step()

                if is_train:
                    iterations += 1

                epoch_loss += loss.item() * len(captions)
                epoch_pp += pp.item() * len(captions)

                # dump batch metrics to tensorboard
                if self.writers is not None and phase in self.writers and is_train:
                    self.writers[phase].add_scalar(f"train/batch_loss", loss.item(), iterations)
                    self.writers[phase].add_scalar(f"train/batch_perplexity", pp.item(), iterations)

            epoch_loss = epoch_loss / len(dataloader.dataset)
            epoch_pp = epoch_pp / len(dataloader.dataset)

            # dump epoch metrics to tensorboard
            if self.writers is not None and phase in self.writers:
                self.writers[phase].add_scalar(f"eval/loss", epoch_loss, epoch)
                self.writers[phase].add_scalar(f"eval/perplexity", epoch_pp, epoch)

        if is_train:
            self.experiment_data['iterations'] = iterations

        return epoch_loss, epoch_pp

    def train_model(self, model, dataloaders, optimizer, criterion, scheduler=None, n_epochs=50):

        best_epoch, best_val_loss = 0, float('+inf')
        past_epochs = self.experiment_data['epochs']
        iterations = self.experiment_data['iterations']

        if self.writers is None:
            self._setup_writers()

        for epoch in range(past_epochs + 1, past_epochs + n_epochs + 1):
            self.experiment_data['epochs'] = epoch
            print(f'Epoch {epoch:02d}/{past_epochs + n_epochs:02d}')

            st = time()
            for phase in self.phases:
                epoch_loss, epoch_pp = self.run_epoch(
                    model, dataloaders[phase], optimizer, criterion, phase=phase
                )

                print(f'  {phase:5s} loss: {epoch_loss:.5f}, perplexity: {epoch_pp:.3f}')

                if phase == 'val' and epoch_loss < best_val_loss:
                    best_epoch, best_val_loss = epoch, epoch_loss
                    model.save(self.experiment_data['best_model_path'])

                model.save(f"{self.experiment_data['model_name']}.e{epoch}.pth")

                if phase == 'train' and scheduler is not None:
                    scheduler.step()

            et = time() - st
            print(f'  epoch time: {et:.2f}s')

        print(f'Best val_loss: {best_val_loss} (epoch: {best_epoch})')

        self.experiment_data['epochs'] = epoch
        self.experiment_data['iterations'] = iterations

        return self.experiment_data

    def close(self):
        for writer in self.writers.values():
            writer.close()
        self.writers = None


def gradient_norm(model, norm_type=2.):
    total_norm = torch.norm(
        torch.stack([torch.norm(p.grad.detach(), norm_type)
                     for p in model.parameters() if p.grad is not None]),
        norm_type
    )
    return total_norm
