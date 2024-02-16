import mongoose from "mongoose";

const ComputeProviderSchema = new mongoose.Schema({
    username: { type: String, required: true },
    email: { type: String, required: true },
    name: { type: String, required: true },
    gpu: { type: String, required: true },
    memory: { type: String, required: true },
    total_count_of_gpus: { type: String, required: true },
    count_of_gpus_per_sever: { type: String, required: true},
    storage_capacity: { type: String, required: true },
    nvidia_interlink: { type: Boolean, required: true },
    cpu_model: { type: String, required: true },
    gpu_availaible_start_date: { type: String, required: true },
    gpu_availaible_end_date: { type: String, required: true },
    available: { type: Boolean, required: true },
    location: { type: String, required: true }
});

export const ComputeProviderModel = mongoose.model('ComputeProvider', ComputeProviderSchema);

export const getComputeProviders = () => ComputeProviderModel.find();

export const getComputeProviderByEmail = (email: string) => ComputeProviderModel.findOne( { email } );

export const getComputeProviderById = (id: string) => ComputeProviderModel.findById(id);
export const createComputeProvider = (values: Record<string, any>) => new ComputeProviderModel(values)
    .save().then((computeprovider) => computeprovider.toObject());

export const deleteComputeProviderById = (id: string) => ComputeProviderModel.findOneAndDelete({ _id: id });
export const updateComputeProviderById = (id: string, values: Record<string, any>) => ComputeProviderModel.findByIdAndUpdate(id, values);
