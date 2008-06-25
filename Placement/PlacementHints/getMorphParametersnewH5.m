function parameters = getMorphParametersnewH5(sourcePath,outputPath)
%
%Writes the Morphology Parameters of all h5 files in a directory to a file
%
%Function takes as a parameter the directory path where the h5 files
%are (sourcePath) , and then loops for it to get all the h5 files, does the
%analysis on the neurons and stores the results in the file
%MorphParameters.txt in the directory specified by outputPath
%
%The format of the output file is as follows
%fileName maxHeightAxon maxDepthAxon maxHeightDendrite maxDepthDendrite
%maxRadiusAxon maxRadiusDendrite maxDiameterDendrite maxDiameterAxon

listFilesArgument = [sourcePath '/*.h5'];
list = dir(listFilesArgument);
filesNB = length(list)

outputFilePath = [outputPath '/MorphoParameters.txt'];
outputFile = fopen(outputFilePath,'w');




for i=1:filesNB
    %get the file name
    fileName = list(i).name;
    %get the file path
    filePath = [sourcePath '/' list(i).name];
    
    %get the information for this neuron
    [RaveledNeuron URaveledNeuron RepairedNeuron Soma ApicalPoint n] = loadNewFileFormat(filePath);
    Neuron = RepairedNeuron;
    
    %get the BRANCH Indices
    axonBranchIndices =find(Neuron.typeInfo==1);
    dendriteBranchIndices = find(Neuron.typeInfo==2 | Neuron.typeInfo==3);
    
    axonIndices =[];
    dendriteIndices=[];
    
    for j= 1:length(axonBranchIndices)
        index= axonBranchIndices(j);
        axonIndices= [axonIndices Neuron.beginnings(index):Neuron.endings(index)];
    end
    
    for j= 1:length(dendriteBranchIndices)
        index = dendriteBranchIndices(j);
        dendriteIndices= [dendriteIndices Neuron.beginnings(index):Neuron.endings(index)];
    end
    
    maxHeightAxon = max(Neuron.Y(axonIndices));
    maxDepthAxon =  min(Neuron.Y(axonIndices));
    maxHeightDendrite =  max(Neuron.Y(dendriteIndices));
    maxDepthDendrite =  min(Neuron.Y(dendriteIndices));
    maxRadiusAxon =  max(abs([Neuron.Z(axonIndices)' Neuron.X(axonIndices)']));
    maxRadiusDendrite = max(abs([Neuron.Z(dendriteIndices)' Neuron.X(dendriteIndices)']));
    maxDiameterDendrite = max (Neuron.Diameter(dendriteIndices));
    maxDiameterAxon = max(Neuron.Diameter(axonIndices));
    
   fprintf(outputFile,'%s\t%f\t%f\t%f\t%f\t%f\t%f\t%f\t%f\n',fileName,maxHeightAxon,maxDepthAxon,maxHeightDendrite,maxDepthDendrite,maxRadiusAxon,maxRadiusDendrite,maxDiameterDendrite, maxDiameterAxon);
end

fclose(outputFile);
end