{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": 1,
   "id": "74963e4a",
   "metadata": {},
   "outputs": [
    {
     "name": "stderr",
     "output_type": "stream",
     "text": [
      "c:\\Users\\Patience\\.conda\\envs\\rag\\Lib\\site-packages\\tqdm\\auto.py:21: TqdmWarning: IProgress not found. Please update jupyter and ipywidgets. See https://ipywidgets.readthedocs.io/en/stable/user_install.html\n",
      "  from .autonotebook import tqdm as notebook_tqdm\n"
     ]
    },
    {
     "name": "stdout",
     "output_type": "stream",
     "text": [
      "正在下载训练集...\n"
     ]
    },
    {
     "name": "stderr",
     "output_type": "stream",
     "text": [
      "Downloading readme: 9.52kB [00:00, 9.52MB/s]\n"
     ]
    },
    {
     "ename": "ValueError",
     "evalue": "Invalid pattern: '**' can only be an entire path component",
     "output_type": "error",
     "traceback": [
      "\u001b[31m---------------------------------------------------------------------------\u001b[39m",
      "\u001b[31mValueError\u001b[39m                                Traceback (most recent call last)",
      "\u001b[36mCell\u001b[39m\u001b[36m \u001b[39m\u001b[32mIn[1]\u001b[39m\u001b[32m, line 42\u001b[39m\n\u001b[32m     35\u001b[39m     \u001b[38;5;28;01mreturn\u001b[39;00m {\n\u001b[32m     36\u001b[39m         \u001b[33m\"\u001b[39m\u001b[33mtrain\u001b[39m\u001b[33m\"\u001b[39m: train_file,\n\u001b[32m     37\u001b[39m         \u001b[33m\"\u001b[39m\u001b[33mdev\u001b[39m\u001b[33m\"\u001b[39m: dev_file,\n\u001b[32m     38\u001b[39m         \u001b[33m\"\u001b[39m\u001b[33mtest\u001b[39m\u001b[33m\"\u001b[39m: test_file\n\u001b[32m     39\u001b[39m     }\n\u001b[32m     41\u001b[39m \u001b[38;5;28;01mif\u001b[39;00m \u001b[34m__name__\u001b[39m == \u001b[33m\"\u001b[39m\u001b[33m__main__\u001b[39m\u001b[33m\"\u001b[39m:\n\u001b[32m---> \u001b[39m\u001b[32m42\u001b[39m     \u001b[43mdownload_hotpotqa_to_local\u001b[49m\u001b[43m(\u001b[49m\u001b[43m)\u001b[49m\n",
      "\u001b[36mCell\u001b[39m\u001b[36m \u001b[39m\u001b[32mIn[1]\u001b[39m\u001b[32m, line 14\u001b[39m, in \u001b[36mdownload_hotpotqa_to_local\u001b[39m\u001b[34m()\u001b[39m\n\u001b[32m     12\u001b[39m \u001b[38;5;66;03m# 下载训练集\u001b[39;00m\n\u001b[32m     13\u001b[39m \u001b[38;5;28mprint\u001b[39m(\u001b[33m\"\u001b[39m\u001b[33m正在下载训练集...\u001b[39m\u001b[33m\"\u001b[39m)\n\u001b[32m---> \u001b[39m\u001b[32m14\u001b[39m train_dataset = \u001b[43mload_dataset\u001b[49m\u001b[43m(\u001b[49m\u001b[33;43m\"\u001b[39;49m\u001b[33;43mhotpot_qa\u001b[39;49m\u001b[33;43m\"\u001b[39;49m\u001b[43m,\u001b[49m\u001b[43m \u001b[49m\u001b[33;43m\"\u001b[39;49m\u001b[33;43mdistractor\u001b[39;49m\u001b[33;43m\"\u001b[39;49m\u001b[43m,\u001b[49m\u001b[43m \u001b[49m\u001b[43msplit\u001b[49m\u001b[43m=\u001b[49m\u001b[33;43m\"\u001b[39;49m\u001b[33;43mtrain\u001b[39;49m\u001b[33;43m\"\u001b[39;49m\u001b[43m)\u001b[49m\n\u001b[32m     15\u001b[39m train_file = os.path.join(save_dir, \u001b[33m\"\u001b[39m\u001b[33mhotpotqa_train.json\u001b[39m\u001b[33m\"\u001b[39m)\n\u001b[32m     16\u001b[39m train_dataset.to_json(train_file)\n",
      "\u001b[36mFile \u001b[39m\u001b[32mc:\\Users\\Patience\\.conda\\envs\\rag\\Lib\\site-packages\\datasets\\load.py:2106\u001b[39m, in \u001b[36mload_dataset\u001b[39m\u001b[34m(path, name, data_dir, data_files, split, cache_dir, features, download_config, download_mode, verification_mode, ignore_verifications, keep_in_memory, save_infos, revision, token, use_auth_token, task, streaming, num_proc, storage_options, **config_kwargs)\u001b[39m\n\u001b[32m   2101\u001b[39m verification_mode = VerificationMode(\n\u001b[32m   2102\u001b[39m     (verification_mode \u001b[38;5;129;01mor\u001b[39;00m VerificationMode.BASIC_CHECKS) \u001b[38;5;28;01mif\u001b[39;00m \u001b[38;5;129;01mnot\u001b[39;00m save_infos \u001b[38;5;28;01melse\u001b[39;00m VerificationMode.ALL_CHECKS\n\u001b[32m   2103\u001b[39m )\n\u001b[32m   2105\u001b[39m \u001b[38;5;66;03m# Create a dataset builder\u001b[39;00m\n\u001b[32m-> \u001b[39m\u001b[32m2106\u001b[39m builder_instance = \u001b[43mload_dataset_builder\u001b[49m\u001b[43m(\u001b[49m\n\u001b[32m   2107\u001b[39m \u001b[43m    \u001b[49m\u001b[43mpath\u001b[49m\u001b[43m=\u001b[49m\u001b[43mpath\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   2108\u001b[39m \u001b[43m    \u001b[49m\u001b[43mname\u001b[49m\u001b[43m=\u001b[49m\u001b[43mname\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   2109\u001b[39m \u001b[43m    \u001b[49m\u001b[43mdata_dir\u001b[49m\u001b[43m=\u001b[49m\u001b[43mdata_dir\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   2110\u001b[39m \u001b[43m    \u001b[49m\u001b[43mdata_files\u001b[49m\u001b[43m=\u001b[49m\u001b[43mdata_files\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   2111\u001b[39m \u001b[43m    \u001b[49m\u001b[43mcache_dir\u001b[49m\u001b[43m=\u001b[49m\u001b[43mcache_dir\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   2112\u001b[39m \u001b[43m    \u001b[49m\u001b[43mfeatures\u001b[49m\u001b[43m=\u001b[49m\u001b[43mfeatures\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   2113\u001b[39m \u001b[43m    \u001b[49m\u001b[43mdownload_config\u001b[49m\u001b[43m=\u001b[49m\u001b[43mdownload_config\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   2114\u001b[39m \u001b[43m    \u001b[49m\u001b[43mdownload_mode\u001b[49m\u001b[43m=\u001b[49m\u001b[43mdownload_mode\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   2115\u001b[39m \u001b[43m    \u001b[49m\u001b[43mrevision\u001b[49m\u001b[43m=\u001b[49m\u001b[43mrevision\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   2116\u001b[39m \u001b[43m    \u001b[49m\u001b[43mtoken\u001b[49m\u001b[43m=\u001b[49m\u001b[43mtoken\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   2117\u001b[39m \u001b[43m    \u001b[49m\u001b[43mstorage_options\u001b[49m\u001b[43m=\u001b[49m\u001b[43mstorage_options\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   2118\u001b[39m \u001b[43m    \u001b[49m\u001b[43m*\u001b[49m\u001b[43m*\u001b[49m\u001b[43mconfig_kwargs\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   2119\u001b[39m \u001b[43m\u001b[49m\u001b[43m)\u001b[49m\n\u001b[32m   2121\u001b[39m \u001b[38;5;66;03m# Return iterable dataset in case of streaming\u001b[39;00m\n\u001b[32m   2122\u001b[39m \u001b[38;5;28;01mif\u001b[39;00m streaming:\n",
      "\u001b[36mFile \u001b[39m\u001b[32mc:\\Users\\Patience\\.conda\\envs\\rag\\Lib\\site-packages\\datasets\\load.py:1792\u001b[39m, in \u001b[36mload_dataset_builder\u001b[39m\u001b[34m(path, name, data_dir, data_files, cache_dir, features, download_config, download_mode, revision, token, use_auth_token, storage_options, **config_kwargs)\u001b[39m\n\u001b[32m   1790\u001b[39m     download_config = download_config.copy() \u001b[38;5;28;01mif\u001b[39;00m download_config \u001b[38;5;28;01melse\u001b[39;00m DownloadConfig()\n\u001b[32m   1791\u001b[39m     download_config.token = token\n\u001b[32m-> \u001b[39m\u001b[32m1792\u001b[39m dataset_module = \u001b[43mdataset_module_factory\u001b[49m\u001b[43m(\u001b[49m\n\u001b[32m   1793\u001b[39m \u001b[43m    \u001b[49m\u001b[43mpath\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   1794\u001b[39m \u001b[43m    \u001b[49m\u001b[43mrevision\u001b[49m\u001b[43m=\u001b[49m\u001b[43mrevision\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   1795\u001b[39m \u001b[43m    \u001b[49m\u001b[43mdownload_config\u001b[49m\u001b[43m=\u001b[49m\u001b[43mdownload_config\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   1796\u001b[39m \u001b[43m    \u001b[49m\u001b[43mdownload_mode\u001b[49m\u001b[43m=\u001b[49m\u001b[43mdownload_mode\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   1797\u001b[39m \u001b[43m    \u001b[49m\u001b[43mdata_dir\u001b[49m\u001b[43m=\u001b[49m\u001b[43mdata_dir\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   1798\u001b[39m \u001b[43m    \u001b[49m\u001b[43mdata_files\u001b[49m\u001b[43m=\u001b[49m\u001b[43mdata_files\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   1799\u001b[39m \u001b[43m\u001b[49m\u001b[43m)\u001b[49m\n\u001b[32m   1800\u001b[39m \u001b[38;5;66;03m# Get dataset builder class from the processing script\u001b[39;00m\n\u001b[32m   1801\u001b[39m builder_kwargs = dataset_module.builder_kwargs\n",
      "\u001b[36mFile \u001b[39m\u001b[32mc:\\Users\\Patience\\.conda\\envs\\rag\\Lib\\site-packages\\datasets\\load.py:1492\u001b[39m, in \u001b[36mdataset_module_factory\u001b[39m\u001b[34m(path, revision, download_config, download_mode, dynamic_modules_path, data_dir, data_files, **download_kwargs)\u001b[39m\n\u001b[32m   1487\u001b[39m             \u001b[38;5;28;01mif\u001b[39;00m \u001b[38;5;28misinstance\u001b[39m(e1, \u001b[38;5;167;01mFileNotFoundError\u001b[39;00m):\n\u001b[32m   1488\u001b[39m                 \u001b[38;5;28;01mraise\u001b[39;00m \u001b[38;5;167;01mFileNotFoundError\u001b[39;00m(\n\u001b[32m   1489\u001b[39m                     \u001b[33mf\u001b[39m\u001b[33m\"\u001b[39m\u001b[33mCouldn\u001b[39m\u001b[33m'\u001b[39m\u001b[33mt find a dataset script at \u001b[39m\u001b[38;5;132;01m{\u001b[39;00mrelative_to_absolute_path(combined_path)\u001b[38;5;132;01m}\u001b[39;00m\u001b[33m or any data file in the same directory. \u001b[39m\u001b[33m\"\u001b[39m\n\u001b[32m   1490\u001b[39m                     \u001b[33mf\u001b[39m\u001b[33m\"\u001b[39m\u001b[33mCouldn\u001b[39m\u001b[33m'\u001b[39m\u001b[33mt find \u001b[39m\u001b[33m'\u001b[39m\u001b[38;5;132;01m{\u001b[39;00mpath\u001b[38;5;132;01m}\u001b[39;00m\u001b[33m'\u001b[39m\u001b[33m on the Hugging Face Hub either: \u001b[39m\u001b[38;5;132;01m{\u001b[39;00m\u001b[38;5;28mtype\u001b[39m(e1).\u001b[34m__name__\u001b[39m\u001b[38;5;132;01m}\u001b[39;00m\u001b[33m: \u001b[39m\u001b[38;5;132;01m{\u001b[39;00me1\u001b[38;5;132;01m}\u001b[39;00m\u001b[33m\"\u001b[39m\n\u001b[32m   1491\u001b[39m                 ) \u001b[38;5;28;01mfrom\u001b[39;00m\u001b[38;5;250m \u001b[39m\u001b[38;5;28;01mNone\u001b[39;00m\n\u001b[32m-> \u001b[39m\u001b[32m1492\u001b[39m             \u001b[38;5;28;01mraise\u001b[39;00m e1 \u001b[38;5;28;01mfrom\u001b[39;00m\u001b[38;5;250m \u001b[39m\u001b[38;5;28;01mNone\u001b[39;00m\n\u001b[32m   1493\u001b[39m \u001b[38;5;28;01melse\u001b[39;00m:\n\u001b[32m   1494\u001b[39m     \u001b[38;5;28;01mraise\u001b[39;00m \u001b[38;5;167;01mFileNotFoundError\u001b[39;00m(\n\u001b[32m   1495\u001b[39m         \u001b[33mf\u001b[39m\u001b[33m\"\u001b[39m\u001b[33mCouldn\u001b[39m\u001b[33m'\u001b[39m\u001b[33mt find a dataset script at \u001b[39m\u001b[38;5;132;01m{\u001b[39;00mrelative_to_absolute_path(combined_path)\u001b[38;5;132;01m}\u001b[39;00m\u001b[33m or any data file in the same directory.\u001b[39m\u001b[33m\"\u001b[39m\n\u001b[32m   1496\u001b[39m     )\n",
      "\u001b[36mFile \u001b[39m\u001b[32mc:\\Users\\Patience\\.conda\\envs\\rag\\Lib\\site-packages\\datasets\\load.py:1476\u001b[39m, in \u001b[36mdataset_module_factory\u001b[39m\u001b[34m(path, revision, download_config, download_mode, dynamic_modules_path, data_dir, data_files, **download_kwargs)\u001b[39m\n\u001b[32m   1461\u001b[39m         \u001b[38;5;28;01mreturn\u001b[39;00m HubDatasetModuleFactoryWithScript(\n\u001b[32m   1462\u001b[39m             path,\n\u001b[32m   1463\u001b[39m             revision=revision,\n\u001b[32m   (...)\u001b[39m\u001b[32m   1466\u001b[39m             dynamic_modules_path=dynamic_modules_path,\n\u001b[32m   1467\u001b[39m         ).get_module()\n\u001b[32m   1468\u001b[39m     \u001b[38;5;28;01melse\u001b[39;00m:\n\u001b[32m   1469\u001b[39m         \u001b[38;5;28;01mreturn\u001b[39;00m \u001b[43mHubDatasetModuleFactoryWithoutScript\u001b[49m\u001b[43m(\u001b[49m\n\u001b[32m   1470\u001b[39m \u001b[43m            \u001b[49m\u001b[43mpath\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   1471\u001b[39m \u001b[43m            \u001b[49m\u001b[43mrevision\u001b[49m\u001b[43m=\u001b[49m\u001b[43mrevision\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   1472\u001b[39m \u001b[43m            \u001b[49m\u001b[43mdata_dir\u001b[49m\u001b[43m=\u001b[49m\u001b[43mdata_dir\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   1473\u001b[39m \u001b[43m            \u001b[49m\u001b[43mdata_files\u001b[49m\u001b[43m=\u001b[49m\u001b[43mdata_files\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   1474\u001b[39m \u001b[43m            \u001b[49m\u001b[43mdownload_config\u001b[49m\u001b[43m=\u001b[49m\u001b[43mdownload_config\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m   1475\u001b[39m \u001b[43m            \u001b[49m\u001b[43mdownload_mode\u001b[49m\u001b[43m=\u001b[49m\u001b[43mdownload_mode\u001b[49m\u001b[43m,\u001b[49m\n\u001b[32m-> \u001b[39m\u001b[32m1476\u001b[39m \u001b[43m        \u001b[49m\u001b[43m)\u001b[49m\u001b[43m.\u001b[49m\u001b[43mget_module\u001b[49m\u001b[43m(\u001b[49m\u001b[43m)\u001b[49m\n\u001b[32m   1477\u001b[39m \u001b[38;5;28;01mexcept\u001b[39;00m (\n\u001b[32m   1478\u001b[39m     \u001b[38;5;167;01mException\u001b[39;00m\n\u001b[32m   1479\u001b[39m ) \u001b[38;5;28;01mas\u001b[39;00m e1:  \u001b[38;5;66;03m# noqa all the attempts failed, before raising the error we should check if the module is already cached.\u001b[39;00m\n\u001b[32m   1480\u001b[39m     \u001b[38;5;28;01mtry\u001b[39;00m:\n",
      "\u001b[36mFile \u001b[39m\u001b[32mc:\\Users\\Patience\\.conda\\envs\\rag\\Lib\\site-packages\\datasets\\load.py:1032\u001b[39m, in \u001b[36mHubDatasetModuleFactoryWithoutScript.get_module\u001b[39m\u001b[34m(self)\u001b[39m\n\u001b[32m   1027\u001b[39m metadata_configs = MetadataConfigs.from_dataset_card_data(dataset_card_data)\n\u001b[32m   1028\u001b[39m dataset_infos = DatasetInfosDict.from_dataset_card_data(dataset_card_data)\n\u001b[32m   1029\u001b[39m patterns = (\n\u001b[32m   1030\u001b[39m     sanitize_patterns(\u001b[38;5;28mself\u001b[39m.data_files)\n\u001b[32m   1031\u001b[39m     \u001b[38;5;28;01mif\u001b[39;00m \u001b[38;5;28mself\u001b[39m.data_files \u001b[38;5;129;01mis\u001b[39;00m \u001b[38;5;129;01mnot\u001b[39;00m \u001b[38;5;28;01mNone\u001b[39;00m\n\u001b[32m-> \u001b[39m\u001b[32m1032\u001b[39m     \u001b[38;5;28;01melse\u001b[39;00m \u001b[43mget_data_patterns\u001b[49m\u001b[43m(\u001b[49m\u001b[43mbase_path\u001b[49m\u001b[43m,\u001b[49m\u001b[43m \u001b[49m\u001b[43mdownload_config\u001b[49m\u001b[43m=\u001b[49m\u001b[38;5;28;43mself\u001b[39;49m\u001b[43m.\u001b[49m\u001b[43mdownload_config\u001b[49m\u001b[43m)\u001b[49m\n\u001b[32m   1033\u001b[39m )\n\u001b[32m   1034\u001b[39m data_files = DataFilesDict.from_patterns(\n\u001b[32m   1035\u001b[39m     patterns,\n\u001b[32m   1036\u001b[39m     base_path=base_path,\n\u001b[32m   1037\u001b[39m     allowed_extensions=ALL_ALLOWED_EXTENSIONS,\n\u001b[32m   1038\u001b[39m     download_config=\u001b[38;5;28mself\u001b[39m.download_config,\n\u001b[32m   1039\u001b[39m )\n\u001b[32m   1040\u001b[39m module_name, default_builder_kwargs = infer_module_for_data_files(\n\u001b[32m   1041\u001b[39m     data_files=data_files,\n\u001b[32m   1042\u001b[39m     path=\u001b[38;5;28mself\u001b[39m.name,\n\u001b[32m   1043\u001b[39m     download_config=\u001b[38;5;28mself\u001b[39m.download_config,\n\u001b[32m   1044\u001b[39m )\n",
      "\u001b[36mFile \u001b[39m\u001b[32mc:\\Users\\Patience\\.conda\\envs\\rag\\Lib\\site-packages\\datasets\\data_files.py:456\u001b[39m, in \u001b[36mget_data_patterns\u001b[39m\u001b[34m(base_path, download_config)\u001b[39m\n\u001b[32m    454\u001b[39m resolver = partial(resolve_pattern, base_path=base_path, download_config=download_config)\n\u001b[32m    455\u001b[39m \u001b[38;5;28;01mtry\u001b[39;00m:\n\u001b[32m--> \u001b[39m\u001b[32m456\u001b[39m     \u001b[38;5;28;01mreturn\u001b[39;00m \u001b[43m_get_data_files_patterns\u001b[49m\u001b[43m(\u001b[49m\u001b[43mresolver\u001b[49m\u001b[43m)\u001b[49m\n\u001b[32m    457\u001b[39m \u001b[38;5;28;01mexcept\u001b[39;00m \u001b[38;5;167;01mFileNotFoundError\u001b[39;00m:\n\u001b[32m    458\u001b[39m     \u001b[38;5;28;01mraise\u001b[39;00m EmptyDatasetError(\u001b[33mf\u001b[39m\u001b[33m\"\u001b[39m\u001b[33mThe directory at \u001b[39m\u001b[38;5;132;01m{\u001b[39;00mbase_path\u001b[38;5;132;01m}\u001b[39;00m\u001b[33m doesn\u001b[39m\u001b[33m'\u001b[39m\u001b[33mt contain any data files\u001b[39m\u001b[33m\"\u001b[39m) \u001b[38;5;28;01mfrom\u001b[39;00m\u001b[38;5;250m \u001b[39m\u001b[38;5;28;01mNone\u001b[39;00m\n",
      "\u001b[36mFile \u001b[39m\u001b[32mc:\\Users\\Patience\\.conda\\envs\\rag\\Lib\\site-packages\\datasets\\data_files.py:248\u001b[39m, in \u001b[36m_get_data_files_patterns\u001b[39m\u001b[34m(pattern_resolver)\u001b[39m\n\u001b[32m    246\u001b[39m \u001b[38;5;28;01mfor\u001b[39;00m pattern \u001b[38;5;129;01min\u001b[39;00m patterns:\n\u001b[32m    247\u001b[39m     \u001b[38;5;28;01mtry\u001b[39;00m:\n\u001b[32m--> \u001b[39m\u001b[32m248\u001b[39m         data_files = \u001b[43mpattern_resolver\u001b[49m\u001b[43m(\u001b[49m\u001b[43mpattern\u001b[49m\u001b[43m)\u001b[49m\n\u001b[32m    249\u001b[39m     \u001b[38;5;28;01mexcept\u001b[39;00m \u001b[38;5;167;01mFileNotFoundError\u001b[39;00m:\n\u001b[32m    250\u001b[39m         \u001b[38;5;28;01mcontinue\u001b[39;00m\n",
      "\u001b[36mFile \u001b[39m\u001b[32mc:\\Users\\Patience\\.conda\\envs\\rag\\Lib\\site-packages\\datasets\\data_files.py:332\u001b[39m, in \u001b[36mresolve_pattern\u001b[39m\u001b[34m(pattern, base_path, allowed_extensions, download_config)\u001b[39m\n\u001b[32m    330\u001b[39m     base_path = \u001b[33m\"\u001b[39m\u001b[33m\"\u001b[39m\n\u001b[32m    331\u001b[39m pattern, storage_options = _prepare_path_and_storage_options(pattern, download_config=download_config)\n\u001b[32m--> \u001b[39m\u001b[32m332\u001b[39m fs, _, _ = \u001b[43mget_fs_token_paths\u001b[49m\u001b[43m(\u001b[49m\u001b[43mpattern\u001b[49m\u001b[43m,\u001b[49m\u001b[43m \u001b[49m\u001b[43mstorage_options\u001b[49m\u001b[43m=\u001b[49m\u001b[43mstorage_options\u001b[49m\u001b[43m)\u001b[49m\n\u001b[32m    333\u001b[39m fs_base_path = base_path.split(\u001b[33m\"\u001b[39m\u001b[33m::\u001b[39m\u001b[33m\"\u001b[39m)[\u001b[32m0\u001b[39m].split(\u001b[33m\"\u001b[39m\u001b[33m://\u001b[39m\u001b[33m\"\u001b[39m)[-\u001b[32m1\u001b[39m] \u001b[38;5;129;01mor\u001b[39;00m fs.root_marker\n\u001b[32m    334\u001b[39m fs_pattern = pattern.split(\u001b[33m\"\u001b[39m\u001b[33m::\u001b[39m\u001b[33m\"\u001b[39m)[\u001b[32m0\u001b[39m].split(\u001b[33m\"\u001b[39m\u001b[33m://\u001b[39m\u001b[33m\"\u001b[39m)[-\u001b[32m1\u001b[39m]\n",
      "\u001b[36mFile \u001b[39m\u001b[32mc:\\Users\\Patience\\.conda\\envs\\rag\\Lib\\site-packages\\fsspec\\core.py:686\u001b[39m, in \u001b[36mget_fs_token_paths\u001b[39m\u001b[34m(urlpath, mode, num, name_function, storage_options, protocol, expand)\u001b[39m\n\u001b[32m    684\u001b[39m     paths = _expand_paths(paths, name_function, num)\n\u001b[32m    685\u001b[39m \u001b[38;5;28;01melif\u001b[39;00m \u001b[33m\"\u001b[39m\u001b[33m*\u001b[39m\u001b[33m\"\u001b[39m \u001b[38;5;129;01min\u001b[39;00m paths:\n\u001b[32m--> \u001b[39m\u001b[32m686\u001b[39m     paths = [f \u001b[38;5;28;01mfor\u001b[39;00m f \u001b[38;5;129;01min\u001b[39;00m \u001b[38;5;28msorted\u001b[39m(\u001b[43mfs\u001b[49m\u001b[43m.\u001b[49m\u001b[43mglob\u001b[49m\u001b[43m(\u001b[49m\u001b[43mpaths\u001b[49m\u001b[43m)\u001b[49m) \u001b[38;5;28;01mif\u001b[39;00m \u001b[38;5;129;01mnot\u001b[39;00m fs.isdir(f)]\n\u001b[32m    687\u001b[39m \u001b[38;5;28;01melse\u001b[39;00m:\n\u001b[32m    688\u001b[39m     paths = [paths]\n",
      "\u001b[36mFile \u001b[39m\u001b[32mc:\\Users\\Patience\\.conda\\envs\\rag\\Lib\\site-packages\\huggingface_hub\\hf_file_system.py:516\u001b[39m, in \u001b[36mHfFileSystem.glob\u001b[39m\u001b[34m(self, path, **kwargs)\u001b[39m\n\u001b[32m    503\u001b[39m \u001b[38;5;250m\u001b[39m\u001b[33;03m\"\"\"\u001b[39;00m\n\u001b[32m    504\u001b[39m \u001b[33;03mFind files by glob-matching.\u001b[39;00m\n\u001b[32m    505\u001b[39m \n\u001b[32m   (...)\u001b[39m\u001b[32m    513\u001b[39m \u001b[33;03m    `List[str]`: List of paths matching the pattern.\u001b[39;00m\n\u001b[32m    514\u001b[39m \u001b[33;03m\"\"\"\u001b[39;00m\n\u001b[32m    515\u001b[39m path = \u001b[38;5;28mself\u001b[39m.resolve_path(path, revision=kwargs.get(\u001b[33m\"\u001b[39m\u001b[33mrevision\u001b[39m\u001b[33m\"\u001b[39m)).unresolve()\n\u001b[32m--> \u001b[39m\u001b[32m516\u001b[39m \u001b[38;5;28;01mreturn\u001b[39;00m \u001b[38;5;28;43msuper\u001b[39;49m\u001b[43m(\u001b[49m\u001b[43m)\u001b[49m\u001b[43m.\u001b[49m\u001b[43mglob\u001b[49m\u001b[43m(\u001b[49m\u001b[43mpath\u001b[49m\u001b[43m,\u001b[49m\u001b[43m \u001b[49m\u001b[43m*\u001b[49m\u001b[43m*\u001b[49m\u001b[43mkwargs\u001b[49m\u001b[43m)\u001b[49m\n",
      "\u001b[36mFile \u001b[39m\u001b[32mc:\\Users\\Patience\\.conda\\envs\\rag\\Lib\\site-packages\\fsspec\\spec.py:639\u001b[39m, in \u001b[36mAbstractFileSystem.glob\u001b[39m\u001b[34m(self, path, maxdepth, **kwargs)\u001b[39m\n\u001b[32m    635\u001b[39m         depth = \u001b[38;5;28;01mNone\u001b[39;00m\n\u001b[32m    637\u001b[39m allpaths = \u001b[38;5;28mself\u001b[39m.find(root, maxdepth=depth, withdirs=\u001b[38;5;28;01mTrue\u001b[39;00m, detail=\u001b[38;5;28;01mTrue\u001b[39;00m, **kwargs)\n\u001b[32m--> \u001b[39m\u001b[32m639\u001b[39m pattern = \u001b[43mglob_translate\u001b[49m\u001b[43m(\u001b[49m\u001b[43mpath\u001b[49m\u001b[43m \u001b[49m\u001b[43m+\u001b[49m\u001b[43m \u001b[49m\u001b[43m(\u001b[49m\u001b[33;43m\"\u001b[39;49m\u001b[33;43m/\u001b[39;49m\u001b[33;43m\"\u001b[39;49m\u001b[43m \u001b[49m\u001b[38;5;28;43;01mif\u001b[39;49;00m\u001b[43m \u001b[49m\u001b[43mends_with_sep\u001b[49m\u001b[43m \u001b[49m\u001b[38;5;28;43;01melse\u001b[39;49;00m\u001b[43m \u001b[49m\u001b[33;43m\"\u001b[39;49m\u001b[33;43m\"\u001b[39;49m\u001b[43m)\u001b[49m\u001b[43m)\u001b[49m\n\u001b[32m    640\u001b[39m pattern = re.compile(pattern)\n\u001b[32m    642\u001b[39m out = {\n\u001b[32m    643\u001b[39m     p: info\n\u001b[32m    644\u001b[39m     \u001b[38;5;28;01mfor\u001b[39;00m p, info \u001b[38;5;129;01min\u001b[39;00m \u001b[38;5;28msorted\u001b[39m(allpaths.items())\n\u001b[32m   (...)\u001b[39m\u001b[32m    649\u001b[39m     )\n\u001b[32m    650\u001b[39m }\n",
      "\u001b[36mFile \u001b[39m\u001b[32mc:\\Users\\Patience\\.conda\\envs\\rag\\Lib\\site-packages\\fsspec\\utils.py:729\u001b[39m, in \u001b[36mglob_translate\u001b[39m\u001b[34m(pat)\u001b[39m\n\u001b[32m    727\u001b[39m     \u001b[38;5;28;01mcontinue\u001b[39;00m\n\u001b[32m    728\u001b[39m \u001b[38;5;28;01melif\u001b[39;00m \u001b[33m\"\u001b[39m\u001b[33m**\u001b[39m\u001b[33m\"\u001b[39m \u001b[38;5;129;01min\u001b[39;00m part:\n\u001b[32m--> \u001b[39m\u001b[32m729\u001b[39m     \u001b[38;5;28;01mraise\u001b[39;00m \u001b[38;5;167;01mValueError\u001b[39;00m(\n\u001b[32m    730\u001b[39m         \u001b[33m\"\u001b[39m\u001b[33mInvalid pattern: \u001b[39m\u001b[33m'\u001b[39m\u001b[33m**\u001b[39m\u001b[33m'\u001b[39m\u001b[33m can only be an entire path component\u001b[39m\u001b[33m\"\u001b[39m\n\u001b[32m    731\u001b[39m     )\n\u001b[32m    732\u001b[39m \u001b[38;5;28;01mif\u001b[39;00m part:\n\u001b[32m    733\u001b[39m     results.extend(_translate(part, \u001b[33mf\u001b[39m\u001b[33m\"\u001b[39m\u001b[38;5;132;01m{\u001b[39;00mnot_sep\u001b[38;5;132;01m}\u001b[39;00m\u001b[33m*\u001b[39m\u001b[33m\"\u001b[39m, not_sep))\n",
      "\u001b[31mValueError\u001b[39m: Invalid pattern: '**' can only be an entire path component"
     ]
    }
   ],
   "source": [
    "from datasets import load_dataset\n",
    "import json\n",
    "import os\n",
    "\n",
    "def download_hotpotqa_to_local():\n",
    "    \"\"\"下载 HotpotQA 数据集到本地\"\"\"\n",
    "    \n",
    "    # 创建保存目录\n",
    "    save_dir = \"hotpotqa_dataset\"\n",
    "    os.makedirs(save_dir, exist_ok=True)\n",
    "    \n",
    "    # 下载训练集\n",
    "    print(\"正在下载训练集...\")\n",
    "    train_dataset = load_dataset(\"hotpot_qa\", \"distractor\", split=\"train\")\n",
    "    train_file = os.path.join(save_dir, \"hotpotqa_train.json\")\n",
    "    train_dataset.to_json(train_file)\n",
    "    print(f\"训练集已保存到: {train_file}\")\n",
    "    \n",
    "    # 下载验证集\n",
    "    print(\"正在下载验证集...\")\n",
    "    dev_dataset = load_dataset(\"hotpot_qa\", \"distractor\", split=\"validation\")\n",
    "    dev_file = os.path.join(save_dir, \"hotpotqa_dev.json\")\n",
    "    dev_dataset.to_json(dev_file)\n",
    "    print(f\"验证集已保存到: {dev_file}\")\n",
    "    \n",
    "    # 下载测试集（如果需要）\n",
    "    print(\"正在下载测试集...\")\n",
    "    test_dataset = load_dataset(\"hotpot_qa\", \"distractor\", split=\"test\")\n",
    "    test_file = os.path.join(save_dir, \"hotpotqa_test.json\")\n",
    "    test_dataset.to_json(test_file)\n",
    "    print(f\"测试集已保存到: {test_file}\")\n",
    "    \n",
    "    print(\"所有数据集下载完成！\")\n",
    "    \n",
    "    return {\n",
    "        \"train\": train_file,\n",
    "        \"dev\": dev_file,\n",
    "        \"test\": test_file\n",
    "    }\n",
    "\n",
    "if __name__ == \"__main__\":\n",
    "    download_hotpotqa_to_local()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "8b501bb6",
   "metadata": {},
   "outputs": [],
   "source": []
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "id": "3ce23147",
   "metadata": {},
   "outputs": [],
   "source": []
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "rag",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.12.11"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
