import pytest
from unittest.mock import patch, MagicMock

# SyzbotDataSet import가 필요함
from src.dataset import SyzbotDataSet, FunctionChange


@pytest.fixture
def sanitized_input():
    return {"id1": "KASAN : bug_type1"}


@pytest.fixture
def syzbot_dataset():
    dataset = SyzbotDataSet()
    return dataset


@patch("util.make_sorted_test_set")
def test_collect_dataset(mock_make_sorted_test_set, sanitized_input, syzbot_dataset):
    mock_make_sorted_test_set.return_value = [
        {
            "vulnerable": "static void smap_release_sock(struct smap_psock *psock, struct sock *sock)\n{\n\tif (refcount_dec_and_test(&psock->refcnt)) {\n\t\ttcp_cleanup_ulp(sock);\n\t\tsmap_stop_sock(psock, sock);\n\t\tclear_bit(SMAP_TX_RUNNING, &psock->state);\n\t\trcu_assign_sk_user_data(sock, NULL);\n\t\tcall_rcu_sched(&psock->rcu, smap_destroy_psock);\n\t}\n}\n",
            "benign": "static void smap_release_sock(struct smap_psock *psock, struct sock *sock)\n{\n\tif (refcount_dec_and_test(&psock->refcnt)) {\n\t\ttcp_cleanup_ulp(sock);\n\t\twrite_lock_bh(&sock->sk_callback_lock);\n\t\tsmap_stop_sock(psock, sock);\n\t\twrite_unlock_bh(&sock->sk_callback_lock);\n\t\tclear_bit(SMAP_TX_RUNNING, &psock->state);\n\t\trcu_assign_sk_user_data(sock, NULL);\n\t\tcall_rcu_sched(&psock->rcu, smap_destroy_psock);\n\t}\n}\n",
        }
    ]

    syzbot_dataset.collect_dataset(sanitized_input)

    assert "KASAN : bug_type1" in syzbot_dataset.dataset
    assert len(syzbot_dataset.dataset["KASAN : bug_type1"]) == 1
    assert (
        syzbot_dataset.dataset["KASAN : bug_type1"][0]["vulnerable"]
        == "static void smap_release_sock(struct smap_psock *psock, struct sock *sock)\n{\n\tif (refcount_dec_and_test(&psock->refcnt)) {\n\t\ttcp_cleanup_ulp(sock);\n\t\tsmap_stop_sock(psock, sock);\n\t\tclear_bit(SMAP_TX_RUNNING, &psock->state);\n\t\trcu_assign_sk_user_data(sock, NULL);\n\t\tcall_rcu_sched(&psock->rcu, smap_destroy_psock);\n\t}\n}\n"
    )
    assert (
        syzbot_dataset.dataset["KASAN : bug_type1"][0]["benign"]
        == "static void smap_release_sock(struct smap_psock *psock, struct sock *sock)\n{\n\tif (refcount_dec_and_test(&psock->refcnt)) {\n\t\ttcp_cleanup_ulp(sock);\n\t\twrite_lock_bh(&sock->sk_callback_lock);\n\t\tsmap_stop_sock(psock, sock);\n\t\twrite_unlock_bh(&sock->sk_callback_lock);\n\t\tclear_bit(SMAP_TX_RUNNING, &psock->state);\n\t\trcu_assign_sk_user_data(sock, NULL);\n\t\tcall_rcu_sched(&psock->rcu, smap_destroy_psock);\n\t}\n}\n"
    )

    # Verify make_sorted_test_set was called with correct argument
    mock_make_sorted_test_set.assert_called_once_with(
        "./data/syzbot-function/KASAN__bug_type1"
    )


@patch("util.make_sorted_test_set")
def test_transform(mock_make_sorted_test_set, sanitized_input, syzbot_dataset):
    # Call transform method
    mock_make_sorted_test_set.return_value = [
        {
            "vulnerable": "static void smap_release_sock(struct smap_psock *psock, struct sock *sock)\n{\n\tif (refcount_dec_and_test(&psock->refcnt)) {\n\t\ttcp_cleanup_ulp(sock);\n\t\tsmap_stop_sock(psock, sock);\n\t\tclear_bit(SMAP_TX_RUNNING, &psock->state);\n\t\trcu_assign_sk_user_data(sock, NULL);\n\t\tcall_rcu_sched(&psock->rcu, smap_destroy_psock);\n\t}\n}\n",
            "benign": "static void smap_release_sock(struct smap_psock *psock, struct sock *sock)\n{\n\tif (refcount_dec_and_test(&psock->refcnt)) {\n\t\ttcp_cleanup_ulp(sock);\n\t\twrite_lock_bh(&sock->sk_callback_lock);\n\t\tsmap_stop_sock(psock, sock);\n\t\twrite_unlock_bh(&sock->sk_callback_lock);\n\t\tclear_bit(SMAP_TX_RUNNING, &psock->state);\n\t\trcu_assign_sk_user_data(sock, NULL);\n\t\tcall_rcu_sched(&psock->rcu, smap_destroy_psock);\n\t}\n}\n",
        }
    ]
    syzbot_dataset.collect_dataset(sanitized_input)
    transformed_data = syzbot_dataset.transform()

    # Assert the transformed data is correct
    assert len(transformed_data) == 1
    assert isinstance(transformed_data[0], FunctionChange)
    assert (
        transformed_data[0].after_code
        == "static void smap_release_sock(struct smap_psock *psock, struct sock *sock)\n{\n\tif (refcount_dec_and_test(&psock->refcnt)) {\n\t\ttcp_cleanup_ulp(sock);\n\t\tsmap_stop_sock(psock, sock);\n\t\tclear_bit(SMAP_TX_RUNNING, &psock->state);\n\t\trcu_assign_sk_user_data(sock, NULL);\n\t\tcall_rcu_sched(&psock->rcu, smap_destroy_psock);\n\t}\n}\n"
    )
    assert (
        transformed_data[0].before_code
        == "static void smap_release_sock(struct smap_psock *psock, struct sock *sock)\n{\n\tif (refcount_dec_and_test(&psock->refcnt)) {\n\t\ttcp_cleanup_ulp(sock);\n\t\twrite_lock_bh(&sock->sk_callback_lock);\n\t\tsmap_stop_sock(psock, sock);\n\t\twrite_unlock_bh(&sock->sk_callback_lock);\n\t\tclear_bit(SMAP_TX_RUNNING, &psock->state);\n\t\trcu_assign_sk_user_data(sock, NULL);\n\t\tcall_rcu_sched(&psock->rcu, smap_destroy_psock);\n\t}\n}\n"
    )
    assert transformed_data[0].bug_type == "bug_type1"
    assert transformed_data[0].commit_id == "None"
    assert transformed_data[0].function_name == "None"
    assert transformed_data[0].before_file == "None"
    assert transformed_data[0].after_file == "None"
