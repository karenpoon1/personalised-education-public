import torch
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix

def probit_correct(bs, bq, ps):
    return 1/(1+torch.exp(-bs-bq-ps))


def train(train_ts, test_ts, meta_data, rng, learning_rate, n_iters):

    nll_train_arr = np.zeros(n_iters)
    S = train_ts.size()[0] # no. of rows
    Q = train_ts.size()[1] # no. of cols

    bs_tensor = torch.randn(S, requires_grad=True, generator=rng)
    bq_tensor = torch.randn(Q, requires_grad=True, generator=rng)
    ws_tensor = torch.randn(S, requires_grad=True, generator=rng)

    for epoch in range(n_iters):

        bs_matrix = bs_tensor.repeat(Q, 1)
        bs_matrix = torch.transpose(bs_matrix, 0, 1)
        bq_matrix = bq_tensor.repeat(S, 1)

        ws_matrix = ws_tensor.repeat(Q, 1)
        ws_matrix = torch.transpose(ws_matrix, 0, 1)
        meta_matrix = meta_data.repeat(S, 1)
        ps_matrix = ws_matrix*meta_matrix
        
        probit_1 = 1/(1+torch.exp(-bs_matrix-bq_matrix-ps_matrix))
        nll = -torch.sum(train_ts*torch.log(probit_1) + (1-train_ts)*torch.log(1-probit_1))
        nll.backward()

        with torch.no_grad():
            bs_tensor -= learning_rate * bs_tensor.grad
            bq_tensor -= learning_rate * bq_tensor.grad
            ws_tensor -= learning_rate * ws_tensor.grad

        # zero the gradients after updating
        bs_tensor.grad.zero_()
        bq_tensor.grad.zero_()
        ws_tensor.grad.zero_()

        if epoch % 100 == 0:
            print(epoch,nll)

        nll_train_arr[epoch] = nll

    return bs_tensor, bq_tensor, ws_tensor, n_iters, nll_train_arr


def predict(bs_tensor, bq_tensor, ws_tensor, test_output_ts, meta_ts, rng):
    
    bs_matrix = bs_tensor.repeat(len(bq_tensor), 1)
    bs_matrix = torch.transpose(bs_matrix, 0, 1)
    bq_matrix = bq_tensor.repeat(len(bs_tensor), 1)

    ws_matrix = ws_tensor.repeat(len(bq_tensor), 1)
    ws_matrix = torch.transpose(ws_matrix, 0, 1)
    meta_matrix = meta_ts.repeat(len(bs_tensor), 1)
    ps_matrix = ws_matrix*meta_matrix
    
    product_params_matrix = probit_correct(bs_matrix, bq_matrix, ps_matrix)

    predictions = torch.bernoulli(product_params_matrix, generator=rng)

    performance = torch.sum(torch.eq(test_output_ts, predictions)) / torch.numel(test_output_ts)
    performance = float(performance)*100

    test_output_ts_reshaped = test_output_ts.reshape(-1).type(torch.int)
    predictions_reshaped = predictions.reshape(-1).type(torch.int)

    conf_matrix = confusion_matrix(test_output_ts_reshaped.numpy(), predictions_reshaped.detach().numpy())
    conf_matrix = conf_matrix*100/torch.numel(test_output_ts)
    
    real_portion = test_output_ts.detach()
    real_portion = real_portion[:50, :]
    sns.heatmap(real_portion, linewidth=0.5)
    plt.title('Real binarised data')
    plt.xlabel('Questions')
    plt.ylabel('Students')
    plt.show()

    predicted_probit_portion = product_params_matrix.detach()
    predicted_probit_portion = predicted_probit_portion[:50, :]
    sns.heatmap(predicted_probit_portion, linewidth=0.5)
    plt.title('Predicted probabilities')
    plt.xlabel('Questions')
    plt.ylabel('Students')
    plt.show()

    predicted_portion = predictions.detach()
    predicted_portion = predicted_portion[:50, :]
    sns.heatmap(predicted_portion, linewidth=0.5)
    plt.title('Predicted output')
    plt.xlabel('Questions')
    plt.ylabel('Students')
    plt.show()

    return product_params_matrix, performance, conf_matrix


def train_product_alternate_quadrants(first_train_quadrant_ts, second_train_quadrant_ts, test_output_ts, meta_ts, rng, learning_rate, n_iters):

    bs_tensor, _, ws_tensor, t_arr, nll_arr = train(second_train_quadrant_ts, test_output_ts, meta_ts[:12], rng, learning_rate, n_iters)
    plt.plot(t_arr, nll_arr)
    plt.title('Training student params')
    plt.ylabel('Negative log likelihood')
    plt.xlabel('epoch')
    plt.show()

    _, bq_tensor, ws_tensor, t_arr, nll_arr = train(first_train_quadrant_ts, test_output_ts, meta_ts, rng, learning_rate, n_iters)
    plt.plot(t_arr, nll_arr)
    plt.title('Training question params')
    plt.ylabel('Negative log likelihood')
    plt.xlabel('epoch')
    plt.show()

    if len(bs_tensor) != test_output_ts.shape[0]:
        bs_tensor = bs_tensor[-test_output_ts.shape[0]:]
    if len(bq_tensor) != test_output_ts.shape[1]:
        bq_tensor = bq_tensor[-test_output_ts.shape[1]:]

    product_params_matrix, performance, conf_matrix = predict(bs_tensor, bq_tensor, test_output_ts, rng)

    print(f"bs (student params): {bs_tensor}")
    print(f"bq (question params): {bq_tensor}")
    print(f"Predicted probabilities: {product_params_matrix}")
    print(f"Percentage accuracy for product baseline: {performance}")
    print(f"Confusion matrix: {conf_matrix}")

    return bs_tensor, bq_tensor, product_params_matrix, performance, conf_matrix


def train_product_upper_left_meta(first_quadrant_ts, train_question_ts, train_student_ts, test_ts, meta_ts, rng, learning_rate, n_iters):
    upper_half_ts = torch.cat([first_quadrant_ts, train_question_ts], dim=1)
    left_half_ts = torch.cat([first_quadrant_ts, train_student_ts], dim=0)
    train_product_alternate_quadrants(upper_half_ts, left_half_ts, test_ts, meta_ts, rng, learning_rate, n_iters)
    # bs_tensor, _, t_arr, nll_arr = train(learning_rate, 90, left_half_ts, rng)
    # _, bq_tensor, t_arr, nll_arr = train(learning_rate, 80, upper_half_ts, rng)
    # product_params_matrix, performance = predict(bs_tensor[-test_output_ts.shape[0]:], bq_tensor[-test_output_ts.shape[1]:], test_output_ts, rng)
    return
