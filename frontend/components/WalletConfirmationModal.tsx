"use client";

import React, { useState } from 'react';
import styles from './WalletConfirmationModal.module.css';
import { authFetch } from '@/lib/auth';
import { API } from '@/lib/api';

interface WalletConfirmationModalProps {
    isOpen: boolean;
    onClose: () => void;
    itemName: string;
    price: number;
    currency: string;
    balance: number;
    onSuccess: (newBalance: number) => void;
}

export const WalletConfirmationModal: React.FC<WalletConfirmationModalProps> = ({
    isOpen,
    onClose,
    itemName,
    price,
    currency,
    balance,
    onSuccess
}) => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    if (!isOpen) return null;

    const remainingBalance = balance - price;

    const handleConfirm = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await authFetch(`${API.users.wallet.spend}?amount=${price}&item_name=${encodeURIComponent(itemName)}`, {
                method: 'POST'
            });

            if (res.ok) {
                const data = await res.json();
                onSuccess(data.new_balance);
                onClose();
            } else {
                const err = await res.json();
                setError(err.detail || 'Failed to process purchase');
            }
        } catch (err) {
            setError('An error occurred. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className={styles.overlay} onClick={onClose}>
            <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
                <div className={styles.header}>
                    <h2>Confirm Purchase</h2>
                    <button className={styles.closeBtn} onClick={onClose}>&times;</button>
                </div>

                <div className={styles.content}>
                    <div className={styles.itemCard}>
                        <div className={styles.itemIcon}>🛍️</div>
                        <div className={styles.itemDetails}>
                            <h3>{itemName}</h3>
                            <p className={styles.price}>{price} {currency}</p>
                        </div>
                    </div>

                    <div className={styles.balanceInfo}>
                        <div className={styles.balanceRow}>
                            <span>Current Balance:</span>
                            <span>{balance} {currency}</span>
                        </div>
                        <div className={`${styles.balanceRow} ${styles.deduction}`}>
                            <span>Price:</span>
                            <span>-{price} {currency}</span>
                        </div>
                        <div className={styles.divider}></div>
                        <div className={`${styles.balanceRow} ${styles.result}`}>
                            <span>Remaining:</span>
                            <span className={remainingBalance < 0 ? styles.insufficient : ''}>
                                {remainingBalance} {currency}
                            </span>
                        </div>
                    </div>

                    {error && <div className={styles.error}>{error}</div>}
                </div>

                <div className={styles.footer}>
                    <button className={styles.cancelBtn} onClick={onClose} disabled={loading}>
                        Cancel
                    </button>
                    <button
                        className={styles.confirmBtn}
                        onClick={handleConfirm}
                        disabled={loading || remainingBalance < 0}
                    >
                        {loading ? 'Processing...' : 'Confirm & Buy'}
                    </button>
                </div>
            </div>
        </div>
    );
};
