const mongoose = require("mongoose");

const galleryLogSchema = new mongoose.Schema(
  {
    userId: {
      type: String,
      trim: true,
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
    photoId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Photo",
      index: true,
    },
    eventType: {
      type: String,
      required: true,
      enum: ["gallery_view", "photo_open", "page_change", "search"],
      index: true,
    },
    query: {
      type: String,
      trim: true,
      maxlength: 200,
    },
    page: {
      type: Number,
      min: 1,
      default: 1,
    },
    pageSize: {
      type: Number,
      min: 1,
      max: 100,
      default: 20,
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
    collection: "gallery_log",
  }
);

galleryLogSchema.index({ eventType: 1, createdAt: -1 });
galleryLogSchema.index({ categoryId: 1, createdAt: -1 });
galleryLogSchema.index({ userId: 1, createdAt: -1 });

module.exports = mongoose.model("GalleryLog", galleryLogSchema);
