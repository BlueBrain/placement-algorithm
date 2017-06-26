function getDifferenceAxonDendrite(filePath, path)
% function that plots histograms showing the difference between Axon
% Heights and Dendrite Heights for each type of neurons


%Types of neurons to be considered
neuronTypes = { 'L2PC','L3PC','L4PC','L5CSPC','L5CHPC','L6CCPC'};

%Number of these types
TypesNB = length(neuronTypes);

%******************LOAD THE FILES NEEDED

%load the morphology parameters file
fid = fopen(filePath);
A =textscan(fid,'%s%f%f%f%f%f%f%f%f');

%get info needed from morphology file (input file)
neuronName = A{1,1};
neuronName = strrep(neuronName,'.h5','');

maxHeightAxon = A{1,2};
maxHeightDendrite = A{1,4};
fclose(fid)

%***********************************

%load the NeuronDB.dat file
fid = fopen(path);
A = textscan(fid,'%s%d%s');

neuron = A{1,1};
layerNB = A{1,2};
type = A{1,3};

fclose(fid)

%***********************************

neuronsNB = length(neuron);

fid = fopen('axoneAbove.txt','wt');
for i=1:TypesNB

    %initializing
    difference=ones(1,neuronsNB)*-100000;
    percentage= ones(1,neuronsNB)*-100000;
    MPIndices=[];
    
    cType = neuronTypes{i};
    cTypeIndices = strmatch(cType,type,'exact');
   
      if isempty(cTypeIndices)
       TEXT = sprintf(' ****************The are no cells defined as %s ****************',cType);
       disp(TEXT)
       continue        
      
      else

        MPIndices(cTypeIndices)= getMorphIndices(cTypeIndices, neuron, neuronName);%get corresponding indices in morphology file
        minus = find (MPIndices==0);
        MPIndices(minus)=[];
        
        difference(MPIndices)= maxHeightAxon(MPIndices)-maxHeightDendrite(MPIndices);%get the difference between Axons' heights and dendrites' heights
        
        axoneAbove (MPIndices, difference, neuronName, cType, fid); % function that print neurons with an axon above the dendrite om a file
        
        percentage(MPIndices) = ((difference(MPIndices)) ./ (maxHeightDendrite(MPIndices)'))*100;
       
        m = find (difference==-100000);
        difference(m)=[];
        percentage (m)=[];

        

       
        
        subplot (3,2,i),hist (difference)
        
        
        %subplot (3,2,i), hist (percentage, 20);
        
        title(cType)
        xlabel('height difference')
        ylabel ('neurons')
      end
end

fclose(fid)