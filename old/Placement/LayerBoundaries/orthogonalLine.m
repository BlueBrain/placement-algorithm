function mOrth= orthogonalLine (coordBottom, corrdL1)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%returns slope of "best" orthogonal line to a set of lines
%In this case set of lines is bottom line and layer1 upper boundary    
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

    %calculating angles of both lines
    angle1= atan(coordBottom(1,1));    
    angle2= atan(corrdL1(1,1));
    
       
    angle =[angle1 angle2];
    a= mean(angle); %finding mean angle
    
    m= tan(a); %deducing a "common" slope
   
    mOrth=-1/m; %find slope of orthogonal line
    
   

