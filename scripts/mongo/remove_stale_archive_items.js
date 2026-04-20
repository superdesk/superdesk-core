/*
 * Remove stale archive items and related records.
 *
 * Collections affected:
 * - published (source by _id/ObjectId date and item_id)
 * - archive (by _id)
 * - archive_versions (by _id_document)
 * - archive_history (by item_id)
 * - published (by item_id)
 * - publish_queue (by item_id)
 * - media_references (by item_id and associated_id)
 * - usage_metrics (by item)
 *
 * Run example (dry run):
 *   mongo "mongodb://host:27017/sd-cp" scripts/mongo/remove_stale_archive_items.js
 *
 * Run example (execute deletes):
 *   mongo "mongodb://host:27017/sd-cp" --eval 'var EXECUTE_DELETE=true' scripts/mongo/remove_stale_archive_items.js
 *
 * Run example (limit to 10 batches):
 *   mongo "mongodb://host:27017/sd-cp" --eval 'var MAX_BATCHES=10' scripts/mongo/remove_stale_archive_items.js
 */

var CUTOFF_ISO = "2026-02-01T00:00:00Z";
var BATCH_SIZE = 1000;
var MAX_BATCHES = typeof MAX_BATCHES === "number" && MAX_BATCHES > 0 ? Math.floor(MAX_BATCHES) : 0;
var EXECUTE_DELETE = typeof EXECUTE_DELETE === "boolean" ? EXECUTE_DELETE : false;

var cutoffDate = new Date(CUTOFF_ISO);
var cutoffObjectId = ObjectId.fromDate(cutoffDate);

if (isNaN(cutoffDate.getTime())) {
    throw new Error("Invalid CUTOFF_ISO value: " + CUTOFF_ISO);
}

if (!EXECUTE_DELETE) {
    print("DRY RUN mode enabled. No documents will be deleted.");
}

print("Cutoff date: " + cutoffDate.toISOString());
print("Cutoff ObjectId: " + cutoffObjectId);
print("Batch size: " + BATCH_SIZE);
print("Max batches: " + (MAX_BATCHES > 0 ? MAX_BATCHES : "unlimited"));

var summary = {
    publishedCandidates: 0,
    archiveDeleted: 0,
    archiveVersionsDeleted: 0,
    archiveHistoryDeleted: 0,
    publishedDeleted: 0,
    publishQueueDeleted: 0,
    mediaReferencesDeleted: 0,
    usageMetricsDeleted: 0,
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

var lastSeenId = null;

while (true) {
    if (MAX_BATCHES > 0 && summary.batches >= MAX_BATCHES) {
        print("Reached MAX_BATCHES limit. Stopping.");
        break;
    }

    var idLookup = { $lt: cutoffObjectId };

    if (lastSeenId !== null) {
        idLookup.$gt = lastSeenId;
    }

    var lookup = {
        _id: idLookup,
        item_id: { $exists: true, $ne: null },
        last_published_version: true,
    };

    var publishedDocs = db
        .getCollection("published")
        .find(lookup, { _id: 1, item_id: 1 })
        .sort({ _id: 1 })
        .limit(BATCH_SIZE)
        .toArray();

    if (!publishedDocs.length) {
        break;
    }

    lastSeenId = publishedDocs[publishedDocs.length - 1]._id;

    var itemIds = [];
    var seenItemIds = {};
    for (var i = 0; i < publishedDocs.length; i++) {
        var publishedItemId = publishedDocs[i].item_id;

        if (!publishedItemId || seenItemIds[publishedItemId]) {
            continue;
        }

        seenItemIds[publishedItemId] = true;
        itemIds.push(publishedItemId);
    }

    if (!itemIds.length) {
        continue;
    }

    summary.batches += 1;
    summary.publishedCandidates += itemIds.length;

    var batchArchiveVersions = countOrDelete("archive_versions", { _id_document: { $in: itemIds } });
    var batchArchiveHistory = countOrDelete("archive_history", { item_id: { $in: itemIds } });
    var batchPublished = countOrDelete("published", { item_id: { $in: itemIds } });
    var batchPublishQueue = countOrDelete("publish_queue", { item_id: { $in: itemIds } });
    var batchMediaRefs = countOrDelete("media_references", { $or: [{ item_id: { $in: itemIds } }, { associated_id: { $in: itemIds } }] });
    var batchUsageMetrics = countOrDelete("usage_metrics", { item: { $in: itemIds } });
    var batchArchive = countOrDelete("archive", { _id: { $in: itemIds } });

    summary.archiveVersionsDeleted += batchArchiveVersions;
    summary.archiveHistoryDeleted += batchArchiveHistory;
    summary.publishedDeleted += batchPublished;
    summary.publishQueueDeleted += batchPublishQueue;
    summary.mediaReferencesDeleted += batchMediaRefs;
    summary.usageMetricsDeleted += batchUsageMetrics;
    summary.archiveDeleted += batchArchive;

    print(
        [
            "Batch " + summary.batches,
            "published_candidates=" + itemIds.length,
            "archive_versions=" + batchArchiveVersions,
            "archive_history=" + batchArchiveHistory,
            "published=" + batchPublished,
            "publish_queue=" + batchPublishQueue,
            "media_references=" + batchMediaRefs,
            "usage_metrics=" + batchUsageMetrics,
            "archive=" + batchArchive,
        ].join(" | ")
    );
}

print("\nSummary");
print("mode=" + (EXECUTE_DELETE ? "DELETE" : "DRY_RUN"));
print("published candidates scanned=" + summary.publishedCandidates);
print("archive_versions " + (EXECUTE_DELETE ? "deleted" : "matched") + "=" + summary.archiveVersionsDeleted);
print("archive_history " + (EXECUTE_DELETE ? "deleted" : "matched") + "=" + summary.archiveHistoryDeleted);
print("published " + (EXECUTE_DELETE ? "deleted" : "matched") + "=" + summary.publishedDeleted);
print("publish_queue " + (EXECUTE_DELETE ? "deleted" : "matched") + "=" + summary.publishQueueDeleted);
print("media_references " + (EXECUTE_DELETE ? "deleted" : "matched") + "=" + summary.mediaReferencesDeleted);
print("usage_metrics " + (EXECUTE_DELETE ? "deleted" : "matched") + "=" + summary.usageMetricsDeleted);
print("archive " + (EXECUTE_DELETE ? "deleted" : "matched") + "=" + summary.archiveDeleted);
print("batches processed=" + summary.batches);
