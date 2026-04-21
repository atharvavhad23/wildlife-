# Wildlife MongoDB Schema Design (No SQL)

This design uses MongoDB collections with Mongoose models and follows normalized references where cardinality is high.

## 1) prediction_input
- Primary Key: `_id` (ObjectId)
- Fields: `vegetationIndex`, `temperature`, `rainfall`, `waterAvailability`, `landUse`, `humanDisturbance`, `locationName`, `coordinates`, `source`, `createdAt`
- Indexes: `createdAt`, `locationName+createdAt`, `coordinates` (2dsphere)
- Relationships: 1:1/1:N with `prediction_result` and `prediction_history`

## 2) prediction_result
- Primary Key: `_id`
- Foreign Keys: `inputId -> prediction_input._id`, `categoryId -> category._id`, `speciesId -> species._id`
- Fields: `predictedDensityPerSqKm`, `confidenceScore`, `modelVersion`, `modelRuntimeMs`, `rawOutput`
- Indexes: `inputId` unique, `categoryId+createdAt`, `speciesId+createdAt`
- Relationships: N:1 with `prediction_input`, optional N:1 with `category`, `species`

## 3) prediction_history
- Primary Key: `_id`
- Foreign Keys: `predictionResultId -> prediction_result._id`, `inputId -> prediction_input._id`
- Fields: `baselineDensityPerSqKm`, `currentDensityPerSqKm`, `changePercent`, `trend`, `sequenceNo`
- Indexes: unique `inputId+sequenceNo`, `locationName+createdAt`, `trend+createdAt`
- Relationships: N:1 with `prediction_result`, `prediction_input`

## 4) alerts
- Primary Key: `_id`
- Foreign Keys: `predictionHistoryId -> prediction_history._id`
- Fields: `severity`, `alertType`, `thresholdValue`, `observedValue`, `message`, `status`, `resolvedAt`
- Indexes: `status+createdAt`, `severity+createdAt`, `alertType+createdAt`
- Relationships: N:1 with `prediction_history`

## 5) category
- Primary Key: `_id`
- Fields: `key` (animals/birds/insects), `name`, `description`, `isActive`
- Indexes: unique `key`
- Relationships: 1:N with `species`, `occurrence`, `photo`

## 6) species
- Primary Key: `_id`
- Foreign Keys: `categoryId -> category._id`
- Fields: `commonName`, `scientificName`, `iucnStatus`, `description`, `tags`, `isActive`
- Indexes: `categoryId+commonName`, unique `categoryId+scientificName`, text index on names/description
- Relationships: N:1 with `category`; 1:N with `occurrence`, `photo`

## 7) occurrence
- Primary Key: `_id`
- Foreign Keys: `speciesId -> species._id`, `categoryId -> category._id`
- Fields: `observationId`, `source`, `observedAt`, `locationName`, `coordinates`, `observerName`, `quantityObserved`, `photoCount`
- Indexes: `coordinates` (2dsphere), `categoryId+observedAt`, `speciesId+observedAt`, `source+observationId`
- Relationships: N:1 with `species`, `category`; 1:N with `photo`

## 8) photo
- Primary Key: `_id`
- Foreign Keys: `occurrenceId -> occurrence._id`, `speciesId -> species._id`, `categoryId -> category._id`
- Fields: `imageUrl`, `thumbnailUrl`, `proxyUrl`, `attribution`, `isPrimary`, `status`, `failedAt`
- Indexes: `categoryId+createdAt`, `speciesId+createdAt`, `occurrenceId+isPrimary+createdAt`, `status+createdAt`
- Relationships: N:1 with `occurrence`, `species`, `category`; 1:N with `image_fallback`

## 9) gallery_log
- Primary Key: `_id`
- Foreign Keys: `categoryId`, `speciesId`, `photoId`
- Fields: `eventType`, `query`, `page`, `pageSize`, `ipAddress`, `userAgent`
- Indexes: `eventType+createdAt`, `categoryId+createdAt`, `userId+createdAt`
- Relationships: optional N:1 with `category`, `species`, `photo`

## 10) image_fallback
- Primary Key: `_id`
- Foreign Keys: `photoId -> photo._id`
- Fields: `originalUrl`, `fallbackUrl`, `proxyUrl`, `failureCode`, `failureReason`, `attemptCount`, `recovered`
- Indexes: `photoId+createdAt`, `recovered+createdAt`
- Relationships: N:1 with `photo`

## 11) cache_log
- Primary Key: `_id`
- Fields: `cacheKey`, `endpoint`, `categoryKey`, `status`, `ttlSeconds`, `expiresAt`, `responseTimeMs`, `payloadSizeBytes`
- Indexes: `cacheKey+createdAt`, `endpoint+status+createdAt`, TTL index on `expiresAt`
- Relationships: standalone telemetry collection

## 12) user_activity
- Primary Key: `_id`
- Foreign Keys: `categoryId`, `speciesId`, `predictionResultId`
- Fields: `sessionId`, `activityType`, `endpoint`, `requestMeta`, `ipAddress`, `userAgent`
- Indexes: `activityType+createdAt`, `userId+createdAt`, `sessionId+createdAt`
- Relationships: optional N:1 with `category`, `species`, `prediction_result`

## Notes for Optimization
- Keep references for high-cardinality relationships (occurrence -> photos).
- Keep small repeated enums and flags indexed only when queried frequently.
- Use 2dsphere index on geo points for future map and radius queries.
- Use TTL index in cache logs to prevent unbounded growth.
- Avoid unbounded embedded arrays to stay safe against MongoDB document size limits.
