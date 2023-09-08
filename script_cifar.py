import os
import tarfile
from torch.utils.data import DataLoader
import functionality_cifar as f
from torchvision.datasets import ImageFolder
import wandb
import torch

wandb.init(
    # set the wandb project where this run will be logged
    project="cluster_CIFAR10_0809",
    name = "cluster_run_1",
    
    # track hyperparameters and run metadata
    config={
    "architecture": "ResNet9",
    "dataset": "CIFAR-10",
    "epochs": 8,
    }
)

from torchvision.datasets.utils import download_url
dataset_url = "https://s3.amazonaws.com/fast-ai-imageclas/cifar10.tgz"
download_url(dataset_url, '.')

# Extract from archive
with tarfile.open('./cifar10.tgz', 'r:gz') as tar:
    tar.extractall(path='./data')
    
# Look into the data directory
data_dir = './data/cifar10'
print(os.listdir(data_dir))
classes = os.listdir(data_dir + "/train")
num_classes = len(classes)
color_channels = 3

print(classes)

train_data = ImageFolder(data_dir+'/train', f.train_tfms)
valid_data = ImageFolder(data_dir+'/test', f.valid_tfms)

batch_size = 128
train_dl = DataLoader(train_data, batch_size, shuffle=True, num_workers=4, pin_memory=True)
test_dl = DataLoader(valid_data, batch_size*2, num_workers=4, pin_memory=True)

device = f.get_default_device()

train_loader = f.DeviceDataLoader(train_dl,device)
test_loader = f.DeviceDataLoader(test_dl,device)

weight_decay = 1e-4
max_lr = 0.01
grad_clip = 0.1
epochs = 8

model = f.to_device(f.ResNet9(color_channels, num_classes))
print(model)
criterion = f.F.cross_entropy()
optimizer = f.torch.optim.Adam(model.parameters(), max_lr, weight_decay=weight_decay)

def train(epoch):
    model.train()
    train_loss = 0
    correct = 0
    total = 0
    for i, batch in enumerate(train_loader):
        images, labels = batch
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs,labels)
        loss.backward()
        optimizer.step()

        train_loss += loss.item()
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += predicted.eq(labels).sum().item()
        if not abs(train_loss) < 0.02:
            wandb.log({"train_loss": train_loss})

def test(epoch):
    global best_acc
    model.eval()
    test_loss = 0
    correct = 0
    total = 0
    with torch.no_grad():
        for i, batch in enumerate(test_loader):
            images, labels = batch
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)
            loss = criterion(outputs, labels)
            test_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()
            if not abs(test_loss) < 0.02:
                wandb.log({"test_loss": test_loss})

        acc = 100.*correct/total
        wandb.log({"acc": acc})
    if acc > best_acc:
        print('Saving..')
        state = {
            'net': model.state_dict(),
            'acc': acc,
            'epoch': epoch,
        }
        if not os.path.isdir('checkpoint'):
            os.mkdir('checkpoint')
        torch.save(state, './checkpoint/ckpt.pth')
        best_acc = acc
        wandb.log({"best_acc": best_acc})

#training loop
scheduler = torch.optim.lr_scheduler.OneCycleLR(optimizer, max_lr, epochs=epochs, 
                                                steps_per_epoch=len(train_loader))

for epoch in range(epochs):
    wandb.log({"epoch": epoch})
    train(epoch)
    test(epoch)
    scheduler.step()
    wandb.log({"learning_rate": float(scheduler.get_lr)})

wandb.finish()
#history += ff.fit(epochs, learning_rate, model, train_loader, val_loader)

# # image = train_data.data[np.random.randint(0,2000)]
# # print(image.shape)
# # print(train_data.classes)
# # plt.imshow(image)
# # plt.show()

# batch_size = 128

# train_dl = DataLoader(train_data, batch_size, shuffle=True, num_workers=4, pin_memory=True)
# test_dl = DataLoader(test_data, batch_size*2, num_workers=4,pin_memory=True)
