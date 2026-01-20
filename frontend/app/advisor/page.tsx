"use client";

import { useState } from 'react';
import styles from './page.module.css';

export default function AdvisorPage() {
    const [file, setFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [status, setStatus] = useState<'idle' | 'analyzing' | 'chatting'>('idle');
    const [messages, setMessages] = useState<any[]>([]);
    const [input, setInput] = useState('');

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selected = e.target.files[0];
            setFile(selected);
            setPreview(URL.createObjectURL(selected));
            setStatus('idle');
        }
    };

    const startAnalysis = () => {
        if (!file) return;
        setStatus('analyzing');

        // Initial AI logic
        setTimeout(() => {
            const initialAnalysis = {
                role: 'assistant',
                text: "I've analyzed this Cashmere Sweater. It's a high-quality piece that matches 92% of your style profile. You have a similar grey merino wool sweater, but this one offers a more formal silhouette. Should we brainstorm some outfits with it?",
                data: {
                    score: 92,
                    similarity: "Grey Merino Wool Sweater (85% match)",
                    outfits: ["Quiet Luxury", "Winter Professional"]
                }
            };
            setMessages([initialAnalysis]);
            setStatus('chatting');
        }, 2500);
    };

    const handleSend = () => {
        if (!input.trim()) return;
        setMessages([...messages, { role: 'user', text: input }]);
        setInput('');

        // Mock follow-up
        setTimeout(() => {
            setMessages(prev => [...prev, {
                role: 'assistant',
                text: "Great question! This would work perfectly with your high-waisted beige shorts for a transition look, or under your navy wool coat for the winter."
            }]);
        }, 1200);
    };

    return (
        <div className={styles.container}>
            <header className={styles.header}>
                <h1>Shopping Advisor</h1>
                <p className="text-muted">Brainstorm potential additions to your closet.</p>
            </header>

            {status === 'idle' && !preview && (
                <label className={styles.dropzone}>
                    <input type="file" accept="image/*" onChange={handleFileChange} hidden />
                    <div className={styles.dropzoneContent}>
                        <div className={styles.icon}>
                            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
                        </div>
                        <span>Upload a Potential Buy</span>
                        <p>Get AI advice before you spend</p>
                    </div>
                </label>
            )}

            {preview && status === 'idle' && (
                <div className={styles.previewStep}>
                    <div className={styles.previewBox}>
                        <img src={preview} alt="Shopping Preview" />
                    </div>
                    <button className={styles.primaryBtn} onClick={startAnalysis}>
                        Consult AI Advisor
                    </button>
                    <button className={styles.ghostBtn} onClick={() => { setPreview(null); setFile(null); }}>
                        Choose Different Item
                    </button>
                </div>
            )}

            {status === 'analyzing' && (
                <div className={styles.analyzingBox}>
                    <div className={styles.spinner} />
                    <h3>Consulting Wardrobe...</h3>
                    <p>AI is comparing this piece with your existing 45 items.</p>
                </div>
            )}

            {status === 'chatting' && (
                <div className={styles.chatInterface}>
                    <div className={styles.itemRef}>
                        <img src={preview!} alt="" className={styles.miniRef} />
                        <div>
                            <h4>Target Item</h4>
                            <span>Potential Purchase</span>
                        </div>
                    </div>

                    <div className={styles.messages}>
                        {messages.map((msg, i) => (
                            <div key={i} className={`${styles.message} ${styles[msg.role]}`}>
                                <div className={styles.bubble}>
                                    {msg.text}
                                    {msg.data && (
                                        <div className={styles.dataCard}>
                                            <div className={styles.scoreRow}>
                                                <span>Value Score: <strong>{msg.data.score}%</strong></span>
                                            </div>
                                            <div className={styles.simRow}>
                                                <span>Similar Item: {msg.data.similarity}</span>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className={styles.chatInput}>
                        <input
                            type="text"
                            placeholder="Ask about versatility, outfits..."
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                        />
                        <button onClick={handleSend} className={styles.sendBtn}>
                            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
