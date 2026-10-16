/**
 * State Manager Core Module - Quản lý trạng thái và Event Bus toàn cục phía Client
 */

class StateStore {
    constructor() {
        this.state = {
            currentUser: null,
            classrooms: [],
            activeSession: null,
            selectedDate: new Date().toISOString().split('T')[0],
        };
        this.listeners = new Map();
    }

    get(key) {
        return this.state[key];
    }

    set(key, value) {
        this.state[key] = value;
        if (this.listeners.has(key)) {
            this.listeners.get(key).forEach(callback => callback(value));
        }
    }

    subscribe(key, callback) {
        if (!this.listeners.has(key)) {
            this.listeners.set(key, new Set());
        }
        this.listeners.get(key).add(callback);
        return () => this.listeners.get(key).delete(callback);
    }
}

export const store = new StateStore();
export default store;
