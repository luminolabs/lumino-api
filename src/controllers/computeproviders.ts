import express from 'express';

import { createComputeProvider, deleteComputeProviderById, getComputeProviderById, getComputeProviders } from '../db/computeprovider';

export const getAllComputeProviders = async (req: express.Request, res: express.Response) => {
    try {
        const computeproviders = await getComputeProviders();

        return res.status(200).json(computeproviders);
    } catch (error) {
        console.log(error);
        return res.sendStatus(400);
    }
};

export const createNewComputeProvider = async (req: express.Request, res: express.Response) => {
    try {
  
      const { username, email, name, resources, available, ipaddress } = req.body;

      const computeProvider = await createComputeProvider({
        email,
        username,
        name,
        resources,
        available,
        ipaddress
      });
      
      return res.status(200).json(computeProvider).end();
    } catch (error) {
      console.log(error);
      return res.sendStatus(400);
    }
  }

export const deleteComputeProvider = async (req: express.Request, res: express.Response) => {
    try {
        const { id } = req.params;

        const deletedComputeProvider = await deleteComputeProviderById(id);

        return res.json(deletedComputeProvider);
    } catch (error) {
        console.log(error);
        return res.sendStatus(400);
    }
}

export const updateComputeProvider = async (req: express.Request, res: express.Response) => {
    try {
      const { id } = req.params;
      const { username } = req.body;
  
      if (!username) {
        return res.sendStatus(400);
      }
  
      const user = await getComputeProviderById(id);
      
      user.username = username;
      await user.save();
  
      return res.status(200).json(user).end();
    } catch (error) {
      console.log(error);
      return res.sendStatus(400);
    }
  }