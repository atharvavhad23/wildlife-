const mongoose = require("mongoose");

const categorySchema = new mongoose.Schema(
  {
    key: {
      type: String,
      required: true,
      trim: true,
      lowercase: true,
      enum: ["animals", "birds", "insects"],
      unique: true,
    },
    name: {
      type: String,
      required: true,
      trim: true,
      unique: true,
      maxlength: 60,
    },
    description: {
      type: String,
      trim: true,
      maxlength: 500,
    },
    isActive: {
      type: Boolean,
      default: true,
      index: true,
    },
  },
  {
    timestamps: true,
    collection: "category",
  }
);

categorySchema.index({ key: 1 }, { unique: true });

module.exports = mongoose.model("Category", categorySchema);
