/*
 * Remove stale Content API items and related records.
 *
 * Collections affected:
 * - items (by _id)
 * - items_versions (by _id_document)
 *
 * Run example (dry run):
 *   mongo "mongodb://host:27017/contentapi" scripts/mongo/remove_stale_content_api_items.js
 *
 * Run example (execute deletes):
 *   mongo "mongodb://host:27017/contentapi" --eval 'var EXECUTE_DELETE=true' scripts/mongo/remove_stale_content_api_items.js
 *
 * Run example (limit to 10 batches):
 *   mongo "mongodb://host:27017/contentapi" --eval 'var MAX_BATCHES=10' scripts/mongo/remove_stale_content_api_items.js
 */

var CUTOFF_ISO = "2026-02-01T00:00:00Z";
var BATCH_SIZE = 1000;
var MAX_BATCHES = typeof MAX_BATCHES === "number" && MAX_BATCHES > 0 ? Math.floor(MAX_BATCHES) : 0;
var EXECUTE_DELETE = typeof EXECUTE_DELETE === "boolean" ? EXECUTE_DELETE : false;

var cutoffDate = new Date(CUTOFF_ISO);

if (isNaN(cutoffDate.getTime())) {
    throw new Error("Invalid CUTOFF_ISO value: " + CUTOFF_ISO);
}

if (!EXECUTE_DELETE) {
    print("DRY RUN mode enabled. No documents will be deleted.");
}

print("Cutoff date: " + cutoffDate.toISOString());
print("Batch size: " + BATCH_SIZE);
print("Max batches: " + (MAX_BATCHES > 0 ? MAX_BATCHES : "unlimited"));

var summary = {
    itemCandidates: 0,
    itemsDeleted: 0,
    itemsVersionsDeleted: 0,
    batches: 0,
};

function countOrDelete(collectionName, query) {
    var collection = db.getCollection(collectionName);

    if (EXECUTE_DELETE) {
        return collection.deleteMany(query).deletedCount;
    }

    if (typeof collection.countDocuments === "function") {
        return collection.countDocuments(query);
    }

    return collection.find(query).count();
}

function unique(values) {
    var seen = {};
    var result = [];

    for (var i = 0; i < values.length; i++) {
        var value = values[i];
        var key = String(value);

        if (!seen[key]) {
            seen[key] = true;
            result.push(value);
        }
    }

    return result;
}

function toStringIds(values) {
    return unique(
        values.map(function (value) {
            return String(value);
        })
    );
}

var lastSeenId = null;

while (true) {
    if (MAX_BATCHES > 0 && summary.batches >= MAX_BATCHES) {
        print("Reached MAX_BATCHES limit. Stopping.");
        break;
    }

    var lookup = {
        _updated: { $lt: cutoffDate },
    };

    if (lastSeenId !== null) {
        lookup._id = { $gt: lastSeenId };
    }

    var itemDocs = db
        .getCollection("items")
        .find(lookup, { _id: 1 })
        .sort({ _id: 1 })
        .limit(BATCH_SIZE)
        .toArray();

    if (!itemDocs.length) {
        break;
    }

    var itemIds = unique(
        itemDocs.map(function (doc) {
            return doc._id;
        })
    );
    var itemIdStrings = toStringIds(itemIds);

    lastSeenId = itemIds[itemIds.length - 1];

    summary.batches += 1;
    summary.itemCandidates += itemIds.length;

    var batchItemsVersions = countOrDelete("items_versions", { _id_document: { $in: itemIdStrings } });
    var batchItems = countOrDelete("items", { _id: { $in: itemIds } });

    summary.itemsVersionsDeleted += batchItemsVersions;
    summary.itemsDeleted += batchItems;

    print(
        [
            "Batch " + summary.batches,
            "candidates=" + itemIds.length,
            "items_versions=" + batchItemsVersions,
            "items=" + batchItems,
        ].join(" | ")
    );
}

print("\nSummary");
print("mode=" + (EXECUTE_DELETE ? "DELETE" : "DRY_RUN"));
print("items candidates scanned=" + summary.itemCandidates);
print("items_versions " + (EXECUTE_DELETE ? "deleted" : "matched") + "=" + summary.itemsVersionsDeleted);
print("items " + (EXECUTE_DELETE ? "deleted" : "matched") + "=" + summary.itemsDeleted);
print("batches processed=" + summary.batches);
