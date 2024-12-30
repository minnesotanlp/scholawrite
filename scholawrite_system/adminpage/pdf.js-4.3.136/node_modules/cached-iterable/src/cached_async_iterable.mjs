import CachedIterable from "./cached_iterable.mjs";

/*
 * CachedAsyncIterable caches the elements yielded by an async iterable.
 *
 * It can be used to iterate over an iterable many times without depleting the
 * iterable.
 */
export default class CachedAsyncIterable extends CachedIterable {
    /**
     * Create an `CachedAsyncIterable` instance.
     *
     * @param {Iterable} iterable
     * @returns {CachedAsyncIterable}
     */
    constructor(iterable) {
        super();

        if (Symbol.asyncIterator in Object(iterable)) {
            this.iterator = iterable[Symbol.asyncIterator]();
        } else if (Symbol.iterator in Object(iterable)) {
            this.iterator = iterable[Symbol.iterator]();
        } else {
            throw new TypeError("Argument must implement the iteration protocol.");
        }
    }

    /**
     * Asynchronous iterator caching the yielded elements.
     *
     * Elements yielded by the original iterable will be cached and available
     * synchronously. Returns an async generator object implementing the
     * iterator protocol over the elements of the original (async or sync)
     * iterable.
     */
    [Symbol.asyncIterator]() {
        const cached = this;
        let cur = 0;

        return {
            async next() {
                if (cached.length <= cur) {
                    cached.push(cached.iterator.next());
                }
                return cached[cur++];
            }
        };
    }

    /**
     * This method allows user to consume the next element from the iterator
     * into the cache.
     *
     * @param {number} count - number of elements to consume
     */
    async touchNext(count = 1) {
        let idx = 0;
        while (idx++ < count) {
            const last = this[this.length - 1];
            if (last && (await last).done) {
                break;
            }
            this.push(this.iterator.next());
        }
        // Return the last cached {value, done} object to allow the calling
        // code to decide if it needs to call touchNext again.
        return this[this.length - 1];
    }
}
