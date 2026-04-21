const mongoose = require("mongoose");

const userActivitySchema = new mongoose.Schema(
  {
    userId: {
      type: String,
      trim: true,
      index: true,
    },
    sessionId: {
      type: String,
      trim: true,
      index: true,
    },
    activityType: {
      type: String,
      required: true,
      enum: [
        "search",
        "prediction_request",
        "prediction_view",
        "species_view",
        "gallery_view",
        "photo_proxy_request",
      ],
      index: true,
    },
    endpoint: {
      type: String,
      trim: true,
      maxlength: 200,
      index: true,
    },
    categoryId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Category",
      index: true,
    },
    speciesId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Species",
      index: true,
    },
    predictionResultId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "PredictionResult",
      index: true,
    },
    requestMeta: {
      type: mongoose.Schema.Types.Mixed,
      default: null,
    },
    ipAddress: {
      type: String,
      trim: true,
      maxlength: 64,
    },
    userAgent: {
      type: String,
      trim: true,
      maxlength: 500,
    },
  },
  {
    timestamps: true,
    collection: "user_activity",
  }
);

userActivitySchema.index({ activityType: 1, createdAt: -1 });
userActivitySchema.index({ userId: 1, createdAt: -1 });
userActivitySchema.index({ sessionId: 1, createdAt: -1 });

module.exports = mongoose.model("UserActivity", userActivitySchema);
