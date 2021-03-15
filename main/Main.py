import torch

from utils.Data_loader import CustomDataLoader
from torchvision import transforms as transforms
from matplotlib import pyplot as plt
import numpy as np
# import U_netLWQ
from torch.utils.data import DataLoader, random_split
from Network.Unet_variant import UnetVariant
from utils.tem import visualize
import albumentations as A
from albumentations.pytorch import ToTensorV2

img_dir = 'utils/DRIVE/training/images/img/'
label_dir = 'utils/DRIVE/training/images/label/'
mask_dir = 'utils/DRIVE/training/mask/'
val_percent = 0.2
batch_size = 1
width_out = 420
height_out = 420
train_on_gpu = torch.cuda.is_available()
if not train_on_gpu:
    print('CUDA is not available..... training on CPU')
else:
    print("CUDA is available..... training on GPU")
device = torch.device("cuda:1" if torch.cuda.is_available() else "cpu")
transform = A.Compose([
    A.HorizontalFlip(p=0.3),
    A.VerticalFlip(p=0.3),
    A.RandomRotate90(p=0.3),
    # A.OneOf([A.ElasticTransform(p=0.2, alpha=90, sigma=120 * 0.05, alpha_affine=45 * 0.03),
    #          A.GridDistortion(p=0.2)], p=0.2),
    A.CLAHE(p=0.25),
    A.RandomBrightnessContrast(p=0.25),
    A.RandomGamma(p=0.25),
    # A.Normalize(mean=0.485, std=0.229)
])

transform_label = transforms.Compose([transforms.ToTensor()
                                      ])

dataset = CustomDataLoader(img_dir, label_dir, mask_dir, transform,
                           transform_label=transform_label, image_scale=0.5)
n_val = int(len(dataset) * val_percent)
n_train = int(len(dataset) - n_val)
train, val = random_split(dataset, [n_train, n_val])
train_loader = DataLoader(train, batch_size=8, shuffle=True, num_workers=0, pin_memory=False)
val_loader = DataLoader(val, batch_size=4, shuffle=False, num_workers=0, pin_memory=False)

# for img, label in (train_loader):
#     #img = img.detach().numpy()
#     n,c,h,w =(img.shape)
#     for i in range(n):
#         im = np.squeeze(img[i, :, :, :].numpy())
#         la = np.squeeze(label[i, :, :, :].numpy())
#         visualize(im, la)


model = UnetVariant(1, 1)
print(model)
model.to(device)
if train_on_gpu:
    print('Transferring model to GPU.....')


def soft_dice_loss(inputs, targets):
    num = targets.size(0)
    m1 = inputs.view(num, -1)
    m2 = targets.view(num, -1)
    intersection = (m1 * m2)
    score = 2. * (intersection.sum(1) + 1) / (m1.sum(1) + m2.sum(1) + 1)
    score = 1 - score.sum() / num
    return score


optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min', patience=40, verbose=True)

no_epoch = 250
valid_loss_min = np.inf
val_loss_plot = []
train_loss_plot = []
train_loss_stochastic = []
sig = torch.nn.Sigmoid()
criterion = torch.nn.BCELoss()

for e in range(no_epoch):
    valid_loss = 0
    train_loss = 0
    running_loss = 0
    model.train()
    for images, labels in train_loader:
        if train_on_gpu:
            images = images.to(device)
            labels = labels.to(device)
        optimizer.zero_grad()
        output = model(images)
        if train_on_gpu:
            output = output.to(device)
        # loss = soft_dice_loss(output,labels)
        # output = output.permute(2, 3, 0, 1).contiguous().view(-1, 2)
        # output = output.permute(0, 2, 3, 1).contiguous()
        # m = output.shape[0]
        # output = output.resize(m * width_out * height_out,2)
        # labels = labels.resize(m * width_out * height_out)
        # label = labels.view(-1,1)
        # outputs = outputs.permute(0, 2, 3, 1)
        # outputs.shape =(batch_size, img_cols, img_rows, n_classes)
        # output = outputs.resize(batch_size * width_out * height_out, 2)
        # labels = labels.resize(batch_size * width_out * height_out)
        loss = criterion(output, labels)

        loss.backward()
        optimizer.step()
        scheduler.step(loss.item())
        running_loss += loss.item()
    train_loss_stochastic.append(loss.item())
    model.eval()
    for images, labels in val_loader:
        if train_on_gpu:
            images = images.to(device)
            labels = labels.to(device)
        with torch.no_grad():
            output = model(images)
            if train_on_gpu:
                output = output.to(device)

            loss = criterion(output, labels)
            valid_loss += loss.item()

    valid_loss = valid_loss / len(val_loader)
    val_loss_plot.append(valid_loss)

    train_loss = running_loss / len(train_loader)
    train_loss_plot.append(train_loss)
    print('Epoch :{} \t Training_loss: {} \t Validation_loss: {}'.format(e + 1, train_loss, valid_loss))
    if valid_loss <= valid_loss_min:
        print('validation loss has decreased from ({:.6f}-->{:.6f}. saving model .......'.format(valid_loss_min,
                                                                                                 valid_loss))
        torch.save(model.state_dict(), 'results/model_segmentation.pt')
        valid_loss_min = valid_loss

np.save('results/train_loss_array', train_loss_plot)
np.save('results/validation_loss_array', val_loss_plot)
np.save('results/stochastic_loss', train_loss_stochastic)
model.to('cpu')
torch.save(model.state_dict(), 'results/model_segmentation_last_epoch.pt')
# i = 0
# for img, lbl in val_loader:
#     img.to(device)
#     lbl.to(device)
#     prediction = model(img)
#     prediction = prediction.detach().numpy()
#
#     # logits = logits.detach().numpy()
#
#     print(prediction.shape)
#     prediction = prediction[0][0]
#     plt.imshow(prediction, cmap='bone',
#                vmin=0, vmax=1,
#                interpolation='lanczos')
#     plt.show()
#     plt.imsave('seg' + str(i) + '.jpg', prediction)
#     i = i + 1
# label = label.detach().numpy()
# label = label[0][0]
#
# if __name__ =='__main__':
#
